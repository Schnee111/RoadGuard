"""
ByteTrack Implementation for Road Damage Detection - FIXED VERSION
"""

import numpy as np
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from math import radians, cos, sin, asin, sqrt

# Try scipy, fallback to simple greedy if not available
try:
    from scipy.optimize import linear_sum_assignment
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    print("[WARNING] scipy not found, using greedy matching")


class KalmanFilter:
    """Simple Kalman Filter for bbox tracking"""
    
    def __init__(self):
        self.F = np.eye(8)
        self.F[0, 4] = 1
        self.F[1, 5] = 1
        self.F[2, 6] = 1
        
        self.H = np.eye(4, 8)
        self.Q = np.eye(8) * 0.1
        self.R = np.eye(4) * 1.0
        
        self.x = np.zeros(8)
        self.P = np.eye(8) * 10
    
    def init(self, bbox: List[float]):
        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        
        self.x = np.array([cx, cy, w * h, w / max(h, 1), 0, 0, 0, 0])
        self.P = np.eye(8) * 10
    
    def predict(self) -> np.ndarray:
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q
        return self.x[:4]
    
    def update(self, bbox: List[float]):
        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        
        z = np.array([cx, cy, w * h, w / max(h, 1)])
        S = self.H @ self.P @ self.H.T + self.R
        K = self.P @ self.H.T @ np.linalg.inv(S)
        
        self.x = self.x + K @ (z - self.H @ self.x)
        self.P = (np.eye(8) - K @ self.H) @ self.P
    
    def get_bbox(self) -> List[float]:
        cx, cy, area, ar = self.x[:4]
        w = np.sqrt(max(area * ar, 1))
        h = max(area / w, 1)
        return [cx - w/2, cy - h/2, cx + w/2, cy + h/2]


@dataclass
class STrack:
    """Single track object"""
    track_id: int
    bbox: List[float]
    damage_type: str
    confidence: float
    state: str = 'confirmed'
    frame_id: int = 0
    start_frame: int = 0
    hits: int = 1
    age: int = 0
    first_location: Tuple[float, float] = (0.0, 0.0)
    last_location: Tuple[float, float] = (0.0, 0.0)
    kalman: KalmanFilter = field(default_factory=KalmanFilter)
    is_saved: bool = False
    
    def __post_init__(self):
        self.kalman = KalmanFilter()
        self.kalman.init(self.bbox)
    
    def predict(self):
        self.kalman.predict()
        self.age += 1
    
    def update(self, det: dict, frame_id: int, location: Tuple[float, float]):
        self.bbox = det['bbox']
        self.kalman.update(det['bbox'])
        self.confidence = max(self.confidence, det['conf'])
        self.damage_type = det['type']  # Update type
        self.frame_id = frame_id
        self.last_location = location
        self.hits += 1
        self.age = 0
    
    def get_predicted_bbox(self) -> List[float]:
        return self.kalman.get_bbox()


class ByteTracker:
    """
    ByteTrack for Road Damage Detection
    
    Key fixes:
    1. Lower thresholds for matching
    2. ALL unmatched detections create new tracks (not just high conf)
    3. Better IoU calculation with center distance fallback
    """
    
    TYPE_GROUPS = {
        'pothole': ['D40', 'D43', 'D44', 'Pothole', 'Potholes'],
        'longitudinal': ['D00', 'Longitudinal', 'Longitudinal Crack'],
        'transverse': ['D10', 'Transverse', 'Transverse Crack'],
        'alligator': ['D20', 'Alligator', 'Alligator Crack'],
    }
    
    def __init__(self,
                 high_thresh: float = 0.3,       # LOWERED from 0.5
                 low_thresh: float = 0.1,
                 match_thresh: float = 0.3,      # LOWERED from 0.8 (IoU threshold)
                 center_thresh: float = 100,     # Center distance threshold (pixels)
                 max_age: int = 30,
                 min_hits: int = 1,
                 min_distance_meters: float = 10.0):
        
        self.high_thresh = high_thresh
        self.low_thresh = low_thresh
        self.match_thresh = match_thresh
        self.center_thresh = center_thresh
        self.max_age = max_age
        self.min_hits = min_hits
        self.min_distance_meters = min_distance_meters
        
        self.tracks: List[STrack] = []
        self.next_id = 0
        self.frame_id = 0
        
        self.total_damages = 0
        self.damage_counts = defaultdict(int)
        self.recorded_locations: List[Tuple[float, float, str, int]] = []
        self.enable_spatial_dedup = True
        
        # Frame size for normalization
        self.frame_diagonal = 2000
    
    def set_frame_size(self, width: int, height: int):
        self.frame_diagonal = np.sqrt(width**2 + height**2)
        self.center_thresh = self.frame_diagonal * 0.08  # 8% of diagonal
    
    def get_type_group(self, dtype: str) -> str:
        for group, types in self.TYPE_GROUPS.items():
            if dtype in types:
                return group
        return dtype.lower()
    
    def is_type_compatible(self, t1: str, t2: str) -> bool:
        return t1 == t2 or self.get_type_group(t1) == self.get_type_group(t2)
    
    def calculate_iou(self, box1: List[float], box2: List[float]) -> float:
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        
        return inter / max(area1 + area2 - inter, 1e-6)
    
    def calculate_center_dist(self, box1: List[float], box2: List[float]) -> float:
        c1 = ((box1[0] + box1[2]) / 2, (box1[1] + box1[3]) / 2)
        c2 = ((box2[0] + box2[2]) / 2, (box2[1] + box2[3]) / 2)
        return np.sqrt((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2)
    
    def calculate_cost(self, track: STrack, det: dict) -> float:
        """
        Calculate matching cost (lower = better match).
        Uses hybrid of IoU and center distance.
        """
        if not self.is_type_compatible(track.damage_type, det['type']):
            return 1.0  # Max cost
        
        pred_bbox = track.get_predicted_bbox()
        
        iou = self.calculate_iou(pred_bbox, det['bbox'])
        center_dist = self.calculate_center_dist(pred_bbox, det['bbox'])
        
        # IoU cost (0 = perfect match, 1 = no overlap)
        iou_cost = 1.0 - iou
        
        # Distance cost (normalized)
        dist_cost = min(center_dist / self.center_thresh, 1.0)
        
        # Combined cost: prefer IoU if there's overlap, otherwise use distance
        if iou > 0.1:
            cost = 0.6 * iou_cost + 0.4 * dist_cost
        else:
            cost = 0.3 * iou_cost + 0.7 * dist_cost
        
        return cost
    
    def match_detections(self, tracks: List[STrack], dets: List[dict], thresh: float):
        """Match detections to tracks using Hungarian or greedy algorithm"""
        if len(tracks) == 0 or len(dets) == 0:
            return [], list(range(len(tracks))), list(range(len(dets)))
        
        # Build cost matrix
        cost_matrix = np.zeros((len(tracks), len(dets)))
        for t_idx, track in enumerate(tracks):
            for d_idx, det in enumerate(dets):
                cost_matrix[t_idx, d_idx] = self.calculate_cost(track, det)
        
        # Solve assignment
        if HAS_SCIPY:
            row_ind, col_ind = linear_sum_assignment(cost_matrix)
            matched = [(r, c) for r, c in zip(row_ind, col_ind) if cost_matrix[r, c] <= thresh]
        else:
            # Greedy fallback
            matched = []
            flat = [(cost_matrix[i, j], i, j) for i in range(len(tracks)) for j in range(len(dets))]
            flat.sort()
            used_tracks, used_dets = set(), set()
            for cost, t_idx, d_idx in flat:
                if cost > thresh:
                    break
                if t_idx not in used_tracks and d_idx not in used_dets:
                    matched.append((t_idx, d_idx))
                    used_tracks.add(t_idx)
                    used_dets.add(d_idx)
        
        unmatched_tracks = [i for i in range(len(tracks)) if i not in [m[0] for m in matched]]
        unmatched_dets = [i for i in range(len(dets)) if i not in [m[1] for m in matched]]
        
        return matched, unmatched_tracks, unmatched_dets
    
    def haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371000
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        a = sin((lat2-lat1)/2)**2 + cos(lat1) * cos(lat2) * sin((lon2-lon1)/2)**2
        return R * 2 * asin(sqrt(a))
    
    def is_location_recorded(self, lat: float, lon: float, dtype: str, track_id: int) -> bool:
        if not self.enable_spatial_dedup or (lat == 0 and lon == 0):
            return False
        
        type_group = self.get_type_group(dtype)
        for rec_lat, rec_lon, rec_group, rec_id in self.recorded_locations:
            if rec_id == track_id or rec_group != type_group:
                continue
            if self.haversine(lat, lon, rec_lat, rec_lon) < self.min_distance_meters:
                return True
        return False
    
    def update(self, detections: List[dict], location: Tuple[float, float] = (0, 0)) -> List[dict]:
        """Main update function"""
        self.frame_id += 1
        new_damages = []
        
        if not detections:
            # Age all tracks
            for track in self.tracks:
                track.age += 1
            self.tracks = [t for t in self.tracks if t.age <= self.max_age]
            return []
        
        # Split by confidence
        high_dets = [d for d in detections if d.get('conf', 0.5) >= self.high_thresh]
        low_dets = [d for d in detections if self.low_thresh <= d.get('conf', 0.5) < self.high_thresh]
        all_dets = high_dets + low_dets  # Consider ALL detections
        
        print(f"\n[BYTE] Frame {self.frame_id}: {len(all_dets)} dets ({len(high_dets)} high, {len(low_dets)} low), {len(self.tracks)} tracks")
        
        # Predict all tracks
        for track in self.tracks:
            track.predict()
        
        # ========== MATCH ALL DETECTIONS ==========
        # Use lower threshold for matching
        matched, unmatched_tracks, unmatched_dets = self.match_detections(
            self.tracks, all_dets, thresh=0.7  # Allow up to 0.7 cost
        )
        
        # Update matched tracks
        for t_idx, d_idx in matched:
            track = self.tracks[t_idx]
            det = all_dets[d_idx]
            track.update(det, self.frame_id, location)
            print(f"  [MATCH] Det({det['type']}, {det.get('conf', 0):.2f}) -> Track#{track.track_id} (hits:{track.hits})")
        
        # ========== CREATE NEW TRACKS FOR ALL UNMATCHED ==========
        for d_idx in unmatched_dets:
            det = all_dets[d_idx]
            
            new_track = STrack(
                track_id=self.next_id,
                bbox=det['bbox'],
                damage_type=det['type'],
                confidence=det.get('conf', 0.5),
                state='confirmed',
                frame_id=self.frame_id,
                start_frame=self.frame_id,
                hits=1,
                age=0,
                first_location=location,
                last_location=location,
                is_saved=True
            )
            
            self.tracks.append(new_track)
            self.total_damages += 1
            self.damage_counts[det['type']] += 1
            
            lat, lon = location
            if not self.is_location_recorded(lat, lon, det['type'], new_track.track_id):
                self.recorded_locations.append((lat, lon, self.get_type_group(det['type']), new_track.track_id))
                
                new_damages.append({
                    'track_id': new_track.track_id,
                    'bbox': det['bbox'],
                    'type': det['type'],
                    'conf': det.get('conf', 0.5),
                    'lat': lat,
                    'lon': lon,
                    'first_seen_frame': self.frame_id
                })
                print(f"  [NEW] Track#{new_track.track_id} ({det['type']}, {det.get('conf', 0):.2f}) -> SAVED")
            else:
                print(f"  [SKIP] Track#{new_track.track_id} ({det['type']}) -> Duplicate location")
            
            self.next_id += 1
        
        # ========== REMOVE OLD TRACKS ==========
        self.tracks = [t for t in self.tracks if t.age <= self.max_age]
        
        if new_damages:
            print(f"[BYTE] Total NEW: {len(new_damages)}")
        
        return new_damages
    
    def get_statistics(self) -> dict:
        return {
            'total_damages': self.total_damages,
            'active_tracks': len(self.tracks),
            'damage_by_type': dict(self.damage_counts),
            'frames_processed': self.frame_id
        }
    
    def reset(self):
        self.tracks.clear()
        self.next_id = 0
        self.frame_id = 0
        self.total_damages = 0
        self.damage_counts.clear()
        self.recorded_locations.clear()


# Aliases
SpatialDamageTracker = ByteTracker
DamageTracker = ByteTracker
