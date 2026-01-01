"""
Damage Tracker Module
Menggunakan IoU (Intersection over Union) untuk tracking objek kerusakan jalan.
Memastikan 1 kerusakan hanya dihitung 1 kali (anti-duplikat).
"""

import numpy as np
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import time


@dataclass
class Track:
    """Representasi satu track kerusakan jalan"""
    track_id: int
    bbox: List[float]  # [x1, y1, x2, y2]
    damage_type: str
    confidence: float
    age: int = 0  # Frames sejak terakhir terdeteksi
    total_hits: int = 1  # Berapa kali terdeteksi
    first_seen_frame: int = 0
    last_seen_frame: int = 0
    is_counted: bool = False  # Sudah disimpan ke database atau belum
    first_location: Tuple[float, float] = (0.0, 0.0)  # lat, lon
    

class DamageTracker:
    """
    Object Tracker berbasis IoU untuk menghindari duplikasi deteksi kerusakan jalan.
    
    Cara Kerja:
    1. Setiap deteksi baru dibandingkan dengan track yang ada menggunakan IoU
    2. Jika IoU > threshold, dianggap objek yang sama (update track)
    3. Jika tidak ada yang cocok, buat track baru (kerusakan baru)
    4. Track yang tidak terdeteksi dalam max_age frames akan dihapus
    
    Attributes:
        iou_threshold: Minimum IoU untuk dianggap objek yang sama
        max_age: Maksimum frames sebelum track dihapus jika tidak terdeteksi
        min_hits: Minimum deteksi sebelum track dianggap valid
    """
    
    def __init__(self, iou_threshold: float = 0.3, max_age: int = 45, min_hits: int = 1):
        self.tracks: Dict[int, Track] = {}
        self.next_id: int = 0
        self.iou_threshold = iou_threshold
        self.max_age = max_age  # ~1.5 detik pada 30fps
        self.min_hits = min_hits  # Langsung simpan saat terdeteksi pertama kali
        self.frame_count = 0
        
        # Statistik
        self.total_unique_damages = 0
        self.damage_type_counts = defaultdict(int)
    
    def calculate_iou(self, box1: List[float], box2: List[float]) -> float:
        """
        Hitung Intersection over Union antara dua bounding box.
        
        Args:
            box1, box2: Bounding box dalam format [x1, y1, x2, y2]
            
        Returns:
            IoU value antara 0.0 dan 1.0
        """
        # Koordinat intersection
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        
        # Area intersection
        inter_width = max(0, x2 - x1)
        inter_height = max(0, y2 - y1)
        inter_area = inter_width * inter_height
        
        # Area masing-masing box
        box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
        box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
        
        # Union area
        union_area = box1_area + box2_area - inter_area
        
        # Hindari division by zero
        if union_area <= 0:
            return 0.0
            
        return inter_area / union_area
    
    def calculate_center_distance(self, box1: List[float], box2: List[float]) -> float:
        """Hitung jarak euclidean antara center dua bounding box (normalized)"""
        c1_x = (box1[0] + box1[2]) / 2
        c1_y = (box1[1] + box1[3]) / 2
        c2_x = (box2[0] + box2[2]) / 2
        c2_y = (box2[1] + box2[3]) / 2
        
        return np.sqrt((c1_x - c2_x)**2 + (c1_y - c2_y)**2)
    
    def update(self, detections: List[dict], current_location: Tuple[float, float] = (0, 0)) -> List[dict]:
        """
        Update tracker dengan deteksi frame saat ini.
        
        Args:
            detections: List of {"bbox": [x1,y1,x2,y2], "type": str, "conf": float}
            current_location: (latitude, longitude) lokasi saat ini
            
        Returns:
            new_damages: List deteksi yang BENAR-BENAR BARU dan sudah valid (min_hits tercapai)
        """
        self.frame_count += 1
        new_damages = []
        matched_track_ids = set()
        
        # 1. Match deteksi dengan track yang ada
        for det in detections:
            det_bbox = det["bbox"]
            det_type = det["type"]
            det_conf = det.get("conf", 0.5)
            
            best_match_id = None
            best_iou = 0.0
            
            # Cari track dengan IoU tertinggi
            for track_id, track in self.tracks.items():
                # Hanya match dengan tipe kerusakan yang sama
                if track.damage_type != det_type:
                    continue
                    
                iou = self.calculate_iou(det_bbox, track.bbox)
                
                if iou > best_iou and iou >= self.iou_threshold:
                    best_iou = iou
                    best_match_id = track_id
            
            if best_match_id is not None:
                # Update existing track
                track = self.tracks[best_match_id]
                track.bbox = det_bbox
                track.age = 0
                track.total_hits += 1
                track.last_seen_frame = self.frame_count
                track.confidence = max(track.confidence, det_conf)
                matched_track_ids.add(best_match_id)
                
                # Jika track sudah cukup hits dan belum dihitung, tandai sebagai damage baru
                if track.total_hits >= self.min_hits and not track.is_counted:
                    track.is_counted = True
                    self.total_unique_damages += 1
                    self.damage_type_counts[det_type] += 1
                    
                    new_damages.append({
                        "track_id": best_match_id,
                        "bbox": det_bbox,
                        "type": det_type,
                        "conf": track.confidence,
                        "lat": track.first_location[0],
                        "lon": track.first_location[1],
                        "first_seen_frame": track.first_seen_frame
                    })
            else:
                # Create new track
                new_track = Track(
                    track_id=self.next_id,
                    bbox=det_bbox,
                    damage_type=det_type,
                    confidence=det_conf,
                    age=0,
                    total_hits=1,
                    first_seen_frame=self.frame_count,
                    last_seen_frame=self.frame_count,
                    is_counted=False,
                    first_location=current_location
                )
                self.tracks[self.next_id] = new_track
                matched_track_ids.add(self.next_id)
                
                # Jika min_hits=1, langsung anggap sebagai new damage
                if self.min_hits == 1:
                    new_track.is_counted = True
                    self.total_unique_damages += 1
                    self.damage_type_counts[det_type] += 1
                    
                    new_damages.append({
                        "track_id": self.next_id,
                        "bbox": det_bbox,
                        "type": det_type,
                        "conf": det_conf,
                        "lat": current_location[0],
                        "lon": current_location[1],
                        "first_seen_frame": self.frame_count
                    })
                
                self.next_id += 1
        
        # 2. Age out tracks yang tidak terdeteksi
        tracks_to_remove = []
        for track_id, track in self.tracks.items():
            if track_id not in matched_track_ids:
                track.age += 1
                if track.age > self.max_age:
                    tracks_to_remove.append(track_id)
        
        for tid in tracks_to_remove:
            del self.tracks[tid]
        
        return new_damages
    
    def get_active_tracks(self) -> List[Track]:
        """Dapatkan semua track yang masih aktif"""
        return list(self.tracks.values())
    
    def get_statistics(self) -> dict:
        """Dapatkan statistik tracker"""
        return {
            "total_unique_damages": self.total_unique_damages,
            "active_tracks": len(self.tracks),
            "damage_by_type": dict(self.damage_type_counts),
            "frames_processed": self.frame_count
        }
    
    def reset(self):
        """Reset tracker ke state awal"""
        self.tracks.clear()
        self.next_id = 0
        self.frame_count = 0
        self.total_unique_damages = 0
        self.damage_type_counts.clear()


class SpatialDamageTracker(DamageTracker):
    """
    Extended tracker yang juga mempertimbangkan jarak GPS.
    Berguna untuk mencegah duplikasi saat kendaraan melewati lokasi yang sama dua kali.
    """
    
    def __init__(self, iou_threshold: float = 0.3, max_age: int = 45, 
                 min_hits: int = 1, min_distance_meters: float = 5.0):
        super().__init__(iou_threshold, max_age, min_hits)
        self.min_distance_meters = min_distance_meters
        self.recorded_locations: List[Tuple[float, float, str]] = []  # (lat, lon, type)
    
    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Hitung jarak antara dua koordinat GPS dalam meter"""
        from math import radians, cos, sin, asin, sqrt
        
        R = 6371000  # Radius bumi dalam meter
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        
        return R * c
    
    def is_location_recorded(self, lat: float, lon: float, damage_type: str) -> bool:
        """Cek apakah lokasi ini sudah pernah tercatat untuk tipe kerusakan yang sama"""
        for rec_lat, rec_lon, rec_type in self.recorded_locations:
            if rec_type == damage_type:
                distance = self.haversine_distance(lat, lon, rec_lat, rec_lon)
                if distance < self.min_distance_meters:
                    print(f"  [SPATIAL] Location already recorded: {damage_type} at {distance:.1f}m away")
                    return True
        return False
    
    def update(self, detections: List[dict], current_location: Tuple[float, float] = (0, 0)) -> List[dict]:
        """Override update untuk tambahkan pengecekan spatial"""
        
        # Panggil parent update
        new_damages = super().update(detections, current_location)
        
        print(f"[SPATIAL] Parent returned {len(new_damages)} damages, checking locations...")
        
        # Filter berdasarkan jarak GPS (skip jika simulasi dengan lokasi statis)
        filtered_damages = []
        for dmg in new_damages:
            lat, lon = dmg["lat"], dmg["lon"]
            dmg_type = dmg["type"]
            
            # Skip spatial check jika lokasi (0,0) atau tidak valid
            if lat == 0 and lon == 0:
                print(f"  [SPATIAL] Skipping location check (0,0) - adding damage")
                filtered_damages.append(dmg)
                continue
            
            if not self.is_location_recorded(lat, lon, dmg_type):
                self.recorded_locations.append((lat, lon, dmg_type))
                filtered_damages.append(dmg)
                print(f"  [SPATIAL] ✅ New location recorded: {dmg_type}")
            else:
                print(f"  [SPATIAL] ❌ Duplicate location filtered: {dmg_type}")
        
        print(f"[SPATIAL] Final output: {len(filtered_damages)} damages")
        return filtered_damages
    
    def reset(self):
        """Reset termasuk recorded locations"""
        super().reset()
        self.recorded_locations.clear()
