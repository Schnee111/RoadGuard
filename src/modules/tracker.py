"""
Damage Tracker Module v2.0
Menggunakan kombinasi IoU + Center Distance + Unique ID per detection.
PERBAIKAN: Multiple damages di lokasi GPS sama tidak difilter.
"""

import numpy as np
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from math import radians, cos, sin, asin, sqrt


@dataclass
class Track:
    """Representasi satu track kerusakan jalan"""
    track_id: int
    bbox: List[float]  # [x1, y1, x2, y2]
    damage_type: str
    confidence: float
    age: int = 0
    total_hits: int = 1
    first_seen_frame: int = 0
    last_seen_frame: int = 0
    is_counted: bool = False
    first_location: Tuple[float, float] = (0.0, 0.0)
    last_location: Tuple[float, float] = (0.0, 0.0)
    bbox_history: List[List[float]] = field(default_factory=list)


class DamageTracker:
    """
    Object Tracker v2.0 dengan fitur:
    1. IoU + Center Distance matching (hybrid)
    2. Type-flexible matching (D40 = Pothole)
    3. Track-based dedup (bukan location-based)
    
    KONSEP UTAMA:
    - Setiap DETECTION yang tidak match dengan track = KERUSAKAN BARU
    - Dedup berdasarkan TRACK ID, bukan GPS location
    - 1 Track = 1 Kerusakan (tidak peduli berapa frame terdeteksi)
    """
    
    # Mapping tipe yang bisa saling match
    TYPE_GROUPS = {
        'pothole': ['D40', 'D43', 'D44', 'Pothole', 'Potholes'],
        'longitudinal': ['D00', 'Longitudinal', 'Longitudinal Crack'],
        'transverse': ['D10', 'Transverse', 'Transverse Crack'],
        'alligator': ['D20', 'Alligator', 'Alligator Crack'],
    }
    
    def __init__(self, 
                 iou_threshold: float = 0.15,
                 center_dist_threshold: float = 150,  # pixels
                 max_age: int = 30,  # frames (~1 detik)
                 min_hits: int = 1):
        
        self.tracks: Dict[int, Track] = {}
        self.next_id: int = 0
        self.iou_threshold = iou_threshold
        self.center_dist_threshold = center_dist_threshold
        self.max_age = max_age
        self.min_hits = min_hits
        self.frame_count = 0
        
        # Statistik
        self.total_unique_damages = 0
        self.damage_type_counts = defaultdict(int)
        
        # Frame dimensions (untuk normalize distance)
        self.frame_diagonal = 1500  # Default, akan di-update
    
    def set_frame_size(self, width: int, height: int):
        """Set ukuran frame untuk normalisasi distance threshold"""
        self.frame_diagonal = np.sqrt(width**2 + height**2)
        # Adjust threshold: 10% dari diagonal
        self.center_dist_threshold = self.frame_diagonal * 0.10
        print(f"[TRACKER] Frame size: {width}x{height}, dist threshold: {self.center_dist_threshold:.0f}px")
    
    def get_type_group(self, damage_type: str) -> str:
        """Dapatkan group dari tipe damage"""
        for group, types in self.TYPE_GROUPS.items():
            if damage_type in types:
                return group
        return damage_type.lower()  # Unknown type, use as-is
    
    def is_type_compatible(self, type1: str, type2: str) -> bool:
        """Cek apakah dua tipe bisa dianggap sama"""
        if type1 == type2:
            return True
        return self.get_type_group(type1) == self.get_type_group(type2)
    
    def calculate_iou(self, box1: List[float], box2: List[float]) -> float:
        """Hitung IoU antara dua bbox"""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        
        inter_area = max(0, x2 - x1) * max(0, y2 - y1)
        box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
        box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union_area = box1_area + box2_area - inter_area
        
        if union_area <= 0:
            return 0.0
        return inter_area / union_area
    
    def calculate_center_distance(self, box1: List[float], box2: List[float]) -> float:
        """Hitung jarak center antara dua bbox"""
        c1 = ((box1[0] + box1[2]) / 2, (box1[1] + box1[3]) / 2)
        c2 = ((box2[0] + box2[2]) / 2, (box2[1] + box2[3]) / 2)
        return np.sqrt((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2)
    
    def calculate_match_score(self, det_bbox: List[float], track: Track) -> float:
        """
        Hitung skor matching (0-1).
        Kombinasi IoU dan Center Distance.
        """
        iou = self.calculate_iou(det_bbox, track.bbox)
        center_dist = self.calculate_center_distance(det_bbox, track.bbox)
        
        # Normalize distance (0 = jauh, 1 = dekat)
        dist_score = max(0, 1 - (center_dist / self.center_dist_threshold))
        
        # Weighted average: IoU lebih penting jika overlap, Distance jika tidak
        if iou > 0.1:
            score = 0.7 * iou + 0.3 * dist_score
        else:
            score = 0.3 * iou + 0.7 * dist_score
        
        return score
    
    def update(self, detections: List[dict], current_location: Tuple[float, float] = (0, 0)) -> List[dict]:
        """
        Update tracker dengan deteksi frame saat ini.
        
        Returns:
            List deteksi BARU yang harus disimpan ke database
        """
        self.frame_count += 1
        new_damages = []
        matched_track_ids: Set[int] = set()
        matched_det_indices: Set[int] = set()
        
        # Debug
        if detections:
            print(f"\n[TRACKER] Frame {self.frame_count}: {len(detections)} detections, {len(self.tracks)} active tracks")
        
        # ========== STEP 1: Match detections ke existing tracks ==========
        if self.tracks and detections:
            # Build score matrix
            matches = []
            for det_idx, det in enumerate(detections):
                det_bbox = det["bbox"]
                det_type = det["type"]
                
                for track_id, track in self.tracks.items():
                    # Cek type compatibility
                    if not self.is_type_compatible(det_type, track.damage_type):
                        continue
                    
                    score = self.calculate_match_score(det_bbox, track)
                    if score > 0.2:  # Minimum threshold
                        matches.append((score, det_idx, track_id))
            
            # Sort by score (highest first) dan greedy matching
            matches.sort(reverse=True)
            
            for score, det_idx, track_id in matches:
                if det_idx in matched_det_indices or track_id in matched_track_ids:
                    continue
                
                # Match!
                matched_det_indices.add(det_idx)
                matched_track_ids.add(track_id)
                
                det = detections[det_idx]
                track = self.tracks[track_id]
                
                # Update track
                track.bbox = det["bbox"]
                track.age = 0
                track.total_hits += 1
                track.last_seen_frame = self.frame_count
                track.last_location = current_location
                track.confidence = max(track.confidence, det.get("conf", 0.5))
                
                print(f"  [MATCH] Det#{det_idx} ({det['type']}) -> Track#{track_id} (score: {score:.2f}, hits: {track.total_hits})")
        
        # ========== STEP 2: Create new tracks untuk unmatched detections ==========
        for det_idx, det in enumerate(detections):
            if det_idx in matched_det_indices:
                continue
            
            # DETECTION BARU = KERUSAKAN BARU
            new_track = Track(
                track_id=self.next_id,
                bbox=det["bbox"],
                damage_type=det["type"],
                confidence=det.get("conf", 0.5),
                age=0,
                total_hits=1,
                first_seen_frame=self.frame_count,
                last_seen_frame=self.frame_count,
                is_counted=True,  # Langsung count (min_hits=1)
                first_location=current_location,
                last_location=current_location,
                bbox_history=[det["bbox"].copy()]
            )
            
            self.tracks[self.next_id] = new_track
            self.total_unique_damages += 1
            self.damage_type_counts[det["type"]] += 1
            
            # Return sebagai new damage
            new_damages.append({
                "track_id": self.next_id,
                "bbox": det["bbox"],
                "type": det["type"],
                "conf": det.get("conf", 0.5),
                "lat": current_location[0],
                "lon": current_location[1],
                "first_seen_frame": self.frame_count
            })
            
            print(f"  [NEW] Det#{det_idx} ({det['type']}) -> NEW Track#{self.next_id}")
            
            self.next_id += 1
        
        # ========== STEP 3: Age out old tracks ==========
        tracks_to_remove = []
        for track_id, track in self.tracks.items():
            if track_id not in matched_track_ids:
                track.age += 1
                if track.age > self.max_age:
                    tracks_to_remove.append(track_id)
        
        for tid in tracks_to_remove:
            print(f"  [REMOVE] Track#{tid} aged out")
            del self.tracks[tid]
        
        if new_damages:
            print(f"[TRACKER] Returning {len(new_damages)} NEW damages")
        
        return new_damages
    
    def get_statistics(self) -> dict:
        return {
            "total_unique_damages": self.total_unique_damages,
            "active_tracks": len(self.tracks),
            "damage_by_type": dict(self.damage_type_counts),
            "frames_processed": self.frame_count
        }
    
    def reset(self):
        self.tracks.clear()
        self.next_id = 0
        self.frame_count = 0
        self.total_unique_damages = 0
        self.damage_type_counts.clear()


class SpatialDamageTracker(DamageTracker):
    """
    Extended tracker dengan GPS-based duplicate prevention.
    
    PERBEDAAN PENTING dengan versi lama:
    - Spatial dedup HANYA untuk mencegah SAVE ULANG ke database
    - TIDAK untuk filter detection dalam 1 frame
    - Jika ada 3 pothole berbeda di 1 frame, SEMUA tersimpan dengan track_id berbeda
    
    KAPAN SPATIAL DEDUP AKTIF:
    - Saat kendaraan melewati lokasi yang SAMA di waktu BERBEDA
    - Contoh: Lewat jalan A, putar balik, lewat jalan A lagi
    - Damage yang sudah tersimpan tidak akan tersimpan ulang
    """
    
    def __init__(self, 
                 iou_threshold: float = 0.15,
                 center_dist_threshold: float = 150,
                 max_age: int = 30,
                 min_hits: int = 1,
                 min_distance_meters: float = 10.0):
        
        super().__init__(iou_threshold, center_dist_threshold, max_age, min_hits)
        self.min_distance_meters = min_distance_meters
        
        # Recorded: (lat, lon, type_group, track_id)
        # Track ID untuk mencegah filter damage yang baru dibuat
        self.recorded_damages: List[Tuple[float, float, str, int]] = []
        self.enable_spatial_dedup = True
    
    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Hitung jarak GPS dalam meter"""
        R = 6371000
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        return R * c
    
    def is_already_recorded(self, lat: float, lon: float, damage_type: str, track_id: int) -> bool:
        """
        Cek apakah kerusakan ini sudah pernah direcord.
        HANYA TRUE jika:
        1. Ada damage dengan type group sama
        2. Jaraknya < min_distance
        3. BUKAN dari track yang sama (track_id berbeda)
        """
        type_group = self.get_type_group(damage_type)
        
        for rec_lat, rec_lon, rec_group, rec_track_id in self.recorded_damages:
            # Skip jika dari track yang sama
            if rec_track_id == track_id:
                continue
            
            # Cek type group
            if rec_group != type_group:
                continue
            
            # Cek jarak
            dist = self.haversine_distance(lat, lon, rec_lat, rec_lon)
            if dist < self.min_distance_meters:
                print(f"  [SPATIAL] Already recorded: {damage_type} at {dist:.1f}m from existing")
                return True
        
        return False
    
    def update(self, detections: List[dict], current_location: Tuple[float, float] = (0, 0)) -> List[dict]:
        """Override dengan spatial filtering"""
        
        # Panggil parent update (IoU-based tracking)
        new_damages = super().update(detections, current_location)
        
        if not new_damages:
            return []
        
        # Skip spatial check jika disabled atau GPS tidak valid
        if not self.enable_spatial_dedup or current_location == (0, 0):
            # Record semua damages
            for dmg in new_damages:
                type_group = self.get_type_group(dmg["type"])
                self.recorded_damages.append((dmg["lat"], dmg["lon"], type_group, dmg["track_id"]))
            return new_damages
        
        # Filter berdasarkan spatial (HANYA untuk recorded sebelumnya)
        filtered = []
        for dmg in new_damages:
            lat, lon = dmg["lat"], dmg["lon"]
            
            # Skip check jika GPS invalid
            if lat == 0 and lon == 0:
                filtered.append(dmg)
                type_group = self.get_type_group(dmg["type"])
                self.recorded_damages.append((lat, lon, type_group, dmg["track_id"]))
                continue
            
            # Cek apakah sudah ada di lokasi yang sama
            if not self.is_already_recorded(lat, lon, dmg["type"], dmg["track_id"]):
                filtered.append(dmg)
                type_group = self.get_type_group(dmg["type"])
                self.recorded_damages.append((lat, lon, type_group, dmg["track_id"]))
                print(f"  [SPATIAL] Recorded: Track#{dmg['track_id']} {dmg['type']}")
            else:
                print(f"  [SPATIAL] Filtered duplicate: {dmg['type']}")
        
        return filtered
    
    def reset(self):
        super().reset()
        self.recorded_damages.clear()
