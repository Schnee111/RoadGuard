"""
Database Module for RoadGuard
Menyimpan data kerusakan jalan secara persisten menggunakan SQLite.
"""

import sqlite3
import os
import json
import uuid
import cv2
import base64
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from contextlib import contextmanager


@dataclass
class DamageRecord:
    """Data class untuk satu record kerusakan"""
    id: Optional[int] = None
    track_id: int = 0
    session_id: str = ""
    timestamp: float = 0.0
    latitude: float = 0.0
    longitude: float = 0.0
    damage_type: str = ""
    confidence: float = 0.0
    image_path: str = ""
    bbox: str = ""  # JSON string of [x1, y1, x2, y2]
    created_at: str = ""
    notes: str = ""
    severity: str = "medium"  # low, medium, high


class DamageDatabase:
    """
    SQLite database manager untuk menyimpan data kerusakan jalan.
    
    Features:
    - Penyimpanan persisten kerusakan yang terdeteksi
    - Menyimpan evidence image
    - Query berdasarkan lokasi, tanggal, tipe kerusakan
    - Export ke berbagai format
    """
    
    def __init__(self, db_path: str = "results/roadguard.db", evidence_dir: str = "results/evidence"):
        self.db_path = db_path
        self.evidence_dir = evidence_dir
        
        # Pastikan direktori ada
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        os.makedirs(evidence_dir, exist_ok=True)
        
        # Inisialisasi database
        self._create_tables()
    
    @contextmanager
    def _get_connection(self):
        """Context manager untuk koneksi database"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _create_tables(self):
        """Buat tabel-tabel yang diperlukan"""
        with self._get_connection() as conn:
            # Tabel utama kerusakan
            conn.execute("""
                CREATE TABLE IF NOT EXISTS damages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    track_id INTEGER NOT NULL,
                    session_id TEXT NOT NULL,
                    timestamp REAL DEFAULT 0,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    damage_type TEXT NOT NULL,
                    confidence REAL DEFAULT 0,
                    image_path TEXT,
                    bbox TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT DEFAULT '',
                    severity TEXT DEFAULT 'medium'
                )
            """)
            
            # Tabel sesi inspeksi
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    video_source TEXT,
                    total_damages INTEGER DEFAULT 0,
                    total_distance_km REAL DEFAULT 0,
                    status TEXT DEFAULT 'in_progress',
                    notes TEXT DEFAULT ''
                )
            """)
            
            # Index untuk query yang sering digunakan
            conn.execute("CREATE INDEX IF NOT EXISTS idx_damages_session ON damages(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_damages_type ON damages(damage_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_damages_location ON damages(latitude, longitude)")
    
    def create_session(self, video_source: str = "") -> str:
        """Buat sesi inspeksi baru, return session_id"""
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO sessions (id, start_time, video_source, status)
                VALUES (?, ?, ?, 'in_progress')
            """, (session_id, datetime.now().isoformat(), video_source))
        
        return session_id
    
    def end_session(self, session_id: str, total_distance_km: float = 0):
        """Akhiri sesi inspeksi"""
        with self._get_connection() as conn:
            # Hitung total damages
            cursor = conn.execute(
                "SELECT COUNT(*) FROM damages WHERE session_id = ?", 
                (session_id,)
            )
            total_damages = cursor.fetchone()[0]
            
            conn.execute("""
                UPDATE sessions 
                SET end_time = ?, total_damages = ?, total_distance_km = ?, status = 'completed'
                WHERE id = ?
            """, (datetime.now().isoformat(), total_damages, total_distance_km, session_id))
    
    def save_evidence_image(self, frame, damage_id: int = None) -> str:
        """
        Simpan frame sebagai evidence image.
        
        Args:
            frame: OpenCV image (BGR)
            damage_id: Optional ID untuk penamaan
            
        Returns:
            Path relatif ke file gambar
        """
        filename = f"{uuid.uuid4().hex[:12]}.jpg"
        if damage_id:
            filename = f"dmg_{damage_id}_{filename}"
        
        filepath = os.path.join(self.evidence_dir, filename)
        
        # Resize untuk menghemat storage (max width 640px)
        h, w = frame.shape[:2]
        if w > 640:
            scale = 640 / w
            new_size = (640, int(h * scale))
            frame = cv2.resize(frame, new_size)
        
        cv2.imwrite(filepath, frame)
        return filepath
    
    def insert_damage(self, data: dict, session_id: str, frame=None) -> int:
        """
        Simpan satu record kerusakan.
        
        Args:
            data: Dictionary dengan keys: track_id, timestamp, lat, lon, type, conf, bbox
            session_id: ID sesi inspeksi
            frame: Optional OpenCV image untuk disimpan sebagai evidence
            
        Returns:
            ID record yang baru dibuat
        """
        # Simpan gambar jika ada
        image_path = ""
        if frame is not None:
            image_path = self.save_evidence_image(frame)
        
        # Konversi bbox ke JSON string
        bbox_str = ""
        if "bbox" in data and data["bbox"]:
            bbox_str = json.dumps(data["bbox"])
        
        # Tentukan severity berdasarkan tipe dan confidence
        severity = self._calculate_severity(data.get("type", ""), data.get("conf", 0.5))
        
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO damages (
                    track_id, session_id, timestamp, latitude, longitude,
                    damage_type, confidence, image_path, bbox, severity
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get("track_id", 0),
                session_id,
                data.get("timestamp", 0),
                data.get("lat", 0),
                data.get("lon", 0),
                data.get("type", "Unknown"),
                data.get("conf", 0),
                image_path,
                bbox_str,
                severity
            ))
            return cursor.lastrowid
    
    def _calculate_severity(self, damage_type: str, confidence: float) -> str:
        """Hitung severity berdasarkan tipe dan confidence"""
        # Pothole dan Alligator Crack dianggap lebih parah
        high_severity_types = ["D40", "Pothole", "Lubang", "D20", "Alligator"]
        
        damage_type_lower = damage_type.lower()
        
        if any(t.lower() in damage_type_lower for t in high_severity_types):
            if confidence > 0.7:
                return "high"
            else:
                return "medium"
        else:
            if confidence > 0.8:
                return "medium"
            else:
                return "low"
    
    def get_damages_by_session(self, session_id: str) -> List[DamageRecord]:
        """Ambil semua kerusakan dari satu sesi"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM damages WHERE session_id = ? ORDER BY timestamp
            """, (session_id,))
            
            return [self._row_to_record(row) for row in cursor.fetchall()]
    
    def get_all_damages(self, limit: int = 1000, offset: int = 0) -> List[DamageRecord]:
        """Ambil semua kerusakan dengan pagination"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM damages ORDER BY created_at DESC LIMIT ? OFFSET ?
            """, (limit, offset))
            
            return [self._row_to_record(row) for row in cursor.fetchall()]
    
    def get_damages_in_area(self, lat_min: float, lat_max: float, 
                            lon_min: float, lon_max: float) -> List[DamageRecord]:
        """Ambil kerusakan dalam area tertentu"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM damages 
                WHERE latitude BETWEEN ? AND ? 
                AND longitude BETWEEN ? AND ?
                ORDER BY created_at DESC
            """, (lat_min, lat_max, lon_min, lon_max))
            
            return [self._row_to_record(row) for row in cursor.fetchall()]
    
    def get_damages_by_type(self, damage_type: str) -> List[DamageRecord]:
        """Ambil kerusakan berdasarkan tipe"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM damages 
                WHERE damage_type LIKE ? 
                ORDER BY created_at DESC
            """, (f"%{damage_type}%",))
            
            return [self._row_to_record(row) for row in cursor.fetchall()]
    
    def get_statistics(self) -> dict:
        """Dapatkan statistik keseluruhan"""
        with self._get_connection() as conn:
            # Total damages
            total = conn.execute("SELECT COUNT(*) FROM damages").fetchone()[0]
            
            # Per tipe
            type_counts = {}
            cursor = conn.execute("""
                SELECT damage_type, COUNT(*) as count 
                FROM damages GROUP BY damage_type
            """)
            for row in cursor.fetchall():
                type_counts[row[0]] = row[1]
            
            # Per severity
            severity_counts = {}
            cursor = conn.execute("""
                SELECT severity, COUNT(*) as count 
                FROM damages GROUP BY severity
            """)
            for row in cursor.fetchall():
                severity_counts[row[0]] = row[1]
            
            # Total sessions
            total_sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            
            return {
                "total_damages": total,
                "by_type": type_counts,
                "by_severity": severity_counts,
                "total_sessions": total_sessions
            }
    
    def get_all_sessions(self) -> List[dict]:
        """Ambil semua sesi inspeksi"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM sessions ORDER BY start_time DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def delete_damage(self, damage_id: int):
        """Hapus satu record kerusakan"""
        with self._get_connection() as conn:
            # Ambil image path dulu
            cursor = conn.execute(
                "SELECT image_path FROM damages WHERE id = ?", 
                (damage_id,)
            )
            row = cursor.fetchone()
            if row and row[0] and os.path.exists(row[0]):
                os.remove(row[0])
            
            conn.execute("DELETE FROM damages WHERE id = ?", (damage_id,))
    
    def delete_session(self, session_id: str):
        """Hapus sesi beserta semua damage-nya"""
        with self._get_connection() as conn:
            # Hapus gambar evidence
            cursor = conn.execute(
                "SELECT image_path FROM damages WHERE session_id = ?",
                (session_id,)
            )
            for row in cursor.fetchall():
                if row[0] and os.path.exists(row[0]):
                    os.remove(row[0])
            
            # Hapus records
            conn.execute("DELETE FROM damages WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    
    def export_to_csv(self, filepath: str, session_id: str = None):
        """Export data ke CSV"""
        import csv
        
        if session_id:
            records = self.get_damages_by_session(session_id)
        else:
            records = self.get_all_damages()
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'ID', 'Session', 'Timestamp', 'Latitude', 'Longitude',
                'Type', 'Confidence', 'Severity', 'Created At', 'Image Path'
            ])
            
            for rec in records:
                writer.writerow([
                    rec.id, rec.session_id, rec.timestamp, rec.latitude, rec.longitude,
                    rec.damage_type, rec.confidence, rec.severity, rec.created_at, rec.image_path
                ])
    
    def export_to_geojson(self, filepath: str, session_id: str = None) -> dict:
        """Export data ke GeoJSON"""
        if session_id:
            records = self.get_damages_by_session(session_id)
        else:
            records = self.get_all_damages()
        
        features = []
        for rec in records:
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [rec.longitude, rec.latitude]
                },
                "properties": {
                    "id": rec.id,
                    "damage_type": rec.damage_type,
                    "confidence": rec.confidence,
                    "severity": rec.severity,
                    "timestamp": rec.timestamp,
                    "created_at": rec.created_at,
                    "image_path": rec.image_path
                }
            }
            features.append(feature)
        
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, indent=2)
        
        return geojson
    
    def _row_to_record(self, row) -> DamageRecord:
        """Konversi sqlite Row ke DamageRecord"""
        return DamageRecord(
            id=row['id'],
            track_id=row['track_id'],
            session_id=row['session_id'],
            timestamp=row['timestamp'],
            latitude=row['latitude'],
            longitude=row['longitude'],
            damage_type=row['damage_type'],
            confidence=row['confidence'],
            image_path=row['image_path'] or "",
            bbox=row['bbox'] or "",
            created_at=row['created_at'] or "",
            notes=row['notes'] or "",
            severity=row['severity'] or "medium"
        )
    
    def get_image_base64(self, image_path: str) -> str:
        """Baca gambar dan konversi ke base64 untuk display di web"""
        if not image_path or not os.path.exists(image_path):
            return ""
        
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')


# Singleton instance untuk digunakan di seluruh aplikasi
_db_instance = None

def get_database(db_path: str = "results/roadguard.db") -> DamageDatabase:
    """Dapatkan singleton instance database"""
    global _db_instance
    if _db_instance is None:
        _db_instance = DamageDatabase(db_path)
    return _db_instance
