"""
GPS Manager Module for RoadGuard
Mengelola data GPS dari berbagai sumber: simulasi, CSV, GPX, manual input, atau REALTIME.
"""

import pandas as pd
import numpy as np
import xml.etree.ElementTree as ET
from math import radians, cos, sin, asin, sqrt
from typing import Tuple, Optional, List
from dataclasses import dataclass
from datetime import datetime
import os
import streamlit as st


@dataclass
class GPSPoint:
    """Satu titik GPS"""
    latitude: float
    longitude: float
    timestamp: float = 0.0  # dalam detik
    elevation: float = 0.0
    speed: float = 0.0  # m/s
    accuracy: float = 0.0  # dalam meter


class GPSManager:
    """
    Manager untuk data GPS yang mendukung berbagai sumber input:
    - Simulasi (default)
    - CSV file dengan kolom timestamp, latitude, longitude
    - GPX file (format standar GPS)
    - Manual input (start/end point dengan interpolasi)
    - REALTIME dari browser (HP/Laptop)
    
    Attributes:
        mode: 'simulation', 'csv', 'gpx', 'manual', atau 'realtime'
        data: List of GPSPoint untuk mode file-based
    """
    
    def __init__(self, mode: str = 'simulation', 
                 start_lat: float = -6.9024, 
                 start_lon: float = 107.6188):
        self.mode = mode
        self.data: List[GPSPoint] = []
        
        # Untuk simulasi
        self.start_lat = start_lat
        self.start_lon = start_lon
        self.last_lat = start_lat
        self.last_lon = start_lon
        
        # Untuk manual input
        self.end_lat = start_lat
        self.end_lon = start_lon
        self.total_frames = 0
        
        # Untuk realtime
        self.realtime_lat = None
        self.realtime_lon = None
        self.realtime_accuracy = None
        
        # Track total jarak
        self.total_distance_meters = 0.0
        self._prev_lat = start_lat
        self._prev_lon = start_lon
        
    def set_realtime_mode(self):
        """Set GPS manager ke mode realtime dari browser"""
        self.mode = 'realtime'
        
    def update_realtime_position(self, lat: float, lon: float, accuracy: float = 0.0):
        """
        Update posisi GPS realtime dari browser.
        Dipanggil dari komponen JavaScript.
        
        Args:
            lat: Latitude dari browser
            lon: Longitude dari browser
            accuracy: Akurasi dalam meter
        """
        self.realtime_lat = lat
        self.realtime_lon = lon
        self.realtime_accuracy = accuracy
        
        # Update tracking distance
        if self._prev_lat is not None and self._prev_lon is not None:
            self.total_distance_meters += self.haversine_distance(
                self._prev_lat, self._prev_lon, lat, lon
            )
        
        self._prev_lat = lat
        self._prev_lon = lon
        self.last_lat = lat
        self.last_lon = lon
    
    def get_realtime_position(self) -> Tuple[Optional[float], Optional[float]]:
        """
        Dapatkan posisi GPS realtime terkini.
        
        Returns:
            (latitude, longitude) atau (None, None) jika belum ada data
        """
        # Cek session state dulu (dari JavaScript)
        if 'realtime_gps' in st.session_state and st.session_state['realtime_gps']:
            data = st.session_state['realtime_gps']
            self.realtime_lat = data.get('lat')
            self.realtime_lon = data.get('lon')
            self.realtime_accuracy = data.get('accuracy', 0)
            
        return self.realtime_lat, self.realtime_lon
        
    def load_csv(self, csv_path: str, fps: float = 30.0) -> bool:
        """
        Load data GPS dari file CSV.
        
        Expected columns:
        - timestamp (detik) atau time (HH:MM:SS) atau frame
        - latitude atau lat
        - longitude atau lon atau lng
        
        Args:
            csv_path: Path ke file CSV
            fps: Frame per second video (untuk konversi time ke frame)
            
        Returns:
            True jika berhasil load
        """
        if not os.path.exists(csv_path):
            return False
        
        try:
            df = pd.read_csv(csv_path)
            
            # Cari kolom latitude
            lat_col = None
            for col in ['latitude', 'lat', 'Latitude', 'LAT']:
                if col in df.columns:
                    lat_col = col
                    break
            
            # Cari kolom longitude
            lon_col = None
            for col in ['longitude', 'lon', 'lng', 'Longitude', 'LON', 'LNG']:
                if col in df.columns:
                    lon_col = col
                    break
            
            if lat_col is None or lon_col is None:
                return False
            
            # Cari kolom timestamp
            time_col = None
            for col in ['timestamp', 'time', 'seconds', 'frame', 'Time', 'Timestamp']:
                if col in df.columns:
                    time_col = col
                    break
            
            # Parse data
            self.data = []
            for idx, row in df.iterrows():
                # Determine timestamp
                if time_col:
                    ts_value = row[time_col]
                    if isinstance(ts_value, str) and ':' in ts_value:
                        # Format HH:MM:SS
                        parts = ts_value.split(':')
                        timestamp = float(parts[0])*3600 + float(parts[1])*60 + float(parts[2])
                    else:
                        timestamp = float(ts_value)
                else:
                    # Gunakan index sebagai timestamp (1 row = 1 detik)
                    timestamp = float(idx)
                
                # Elevation opsional
                elevation = 0.0
                for col in ['elevation', 'alt', 'altitude', 'elev']:
                    if col in df.columns:
                        elevation = float(row[col]) if pd.notna(row[col]) else 0.0
                        break
                
                self.data.append(GPSPoint(
                    latitude=float(row[lat_col]),
                    longitude=float(row[lon_col]),
                    timestamp=timestamp,
                    elevation=elevation
                ))
            
            self.mode = 'csv'
            if self.data:
                self.start_lat = self.data[0].latitude
                self.start_lon = self.data[0].longitude
                self.last_lat = self.start_lat
                self.last_lon = self.start_lon
            
            return len(self.data) > 0
            
        except Exception as e:
            print(f"Error loading CSV: {e}")
            return False
    
    def load_gpx(self, gpx_path: str) -> bool:
        """
        Load data GPS dari file GPX.
        
        GPX adalah format standar untuk GPS data, digunakan oleh:
        - Strava, Garmin, dll
        - Apps GPS tracking di HP
        
        Args:
            gpx_path: Path ke file GPX
            
        Returns:
            True jika berhasil load
        """
        if not os.path.exists(gpx_path):
            return False
        
        try:
            tree = ET.parse(gpx_path)
            root = tree.getroot()
            
            # Handle namespace GPX
            ns = {'gpx': 'http://www.topografix.com/GPX/1/1'}
            
            # Coba tanpa namespace dulu
            trkpts = root.findall('.//trkpt')
            if not trkpts:
                # Coba dengan namespace
                trkpts = root.findall('.//gpx:trkpt', ns)
            
            if not trkpts:
                # Coba waypoints
                trkpts = root.findall('.//wpt')
                if not trkpts:
                    trkpts = root.findall('.//gpx:wpt', ns)
            
            self.data = []
            base_time = None
            
            for pt in trkpts:
                lat = float(pt.get('lat'))
                lon = float(pt.get('lon'))
                
                # Elevation
                ele_elem = pt.find('ele') or pt.find('gpx:ele', ns)
                elevation = float(ele_elem.text) if ele_elem is not None else 0.0
                
                # Time
                time_elem = pt.find('time') or pt.find('gpx:time', ns)
                if time_elem is not None:
                    # Parse ISO format: 2024-01-15T10:30:45Z
                    try:
                        dt = datetime.fromisoformat(time_elem.text.replace('Z', '+00:00'))
                        if base_time is None:
                            base_time = dt
                        timestamp = (dt - base_time).total_seconds()
                    except:
                        timestamp = len(self.data)
                else:
                    timestamp = len(self.data)
                
                self.data.append(GPSPoint(
                    latitude=lat,
                    longitude=lon,
                    timestamp=timestamp,
                    elevation=elevation
                ))
            
            self.mode = 'gpx'
            if self.data:
                self.start_lat = self.data[0].latitude
                self.start_lon = self.data[0].longitude
                self.last_lat = self.start_lat
                self.last_lon = self.start_lon
            
            return len(self.data) > 0
            
        except Exception as e:
            print(f"Error loading GPX: {e}")
            return False
    
    def set_manual_route(self, start_lat: float, start_lon: float,
                         end_lat: float, end_lon: float, total_frames: int):
        """
        Set rute manual dengan interpolasi linear dari start ke end.
        
        Args:
            start_lat, start_lon: Koordinat awal
            end_lat, end_lon: Koordinat akhir
            total_frames: Total frame dalam video
        """
        self.mode = 'manual'
        self.start_lat = start_lat
        self.start_lon = start_lon
        self.end_lat = end_lat
        self.end_lon = end_lon
        self.total_frames = max(1, total_frames)
        self.last_lat = start_lat
        self.last_lon = start_lon
    
    def get_location_at_frame(self, frame_idx: int, fps: float = 30.0) -> Tuple[float, float]:
        """
        Ambil lokasi GPS pada frame tertentu.
        
        Args:
            frame_idx: Nomor frame (0-indexed)
            fps: Frame per second video
            
        Returns:
            (latitude, longitude)
        """
        lat, lon = 0.0, 0.0
        
        if self.mode == 'realtime':
            # Untuk realtime, ambil dari session state / last known position
            rt_lat, rt_lon = self.get_realtime_position()
            if rt_lat is not None and rt_lon is not None:
                lat, lon = rt_lat, rt_lon
            else:
                # Fallback ke simulasi jika belum ada data realtime
                lat, lon = self._get_simulated_location(frame_idx)
        
        elif self.mode == 'simulation':
            lat, lon = self._get_simulated_location(frame_idx)
            
        elif self.mode in ['csv', 'gpx'] and self.data:
            lat, lon = self._get_interpolated_location(frame_idx, fps)
            
        elif self.mode == 'manual':
            lat, lon = self._get_manual_location(frame_idx)
            
        else:
            lat, lon = self._get_simulated_location(frame_idx)
        
        # Update tracking
        if lat != 0.0 and lon != 0.0:
            self.total_distance_meters += self.haversine_distance(
                self._prev_lat, self._prev_lon, lat, lon
            )
            self._prev_lat = lat
            self._prev_lon = lon
            self.last_lat = lat
            self.last_lon = lon
        
        return lat, lon
    
    def _get_simulated_location(self, frame_idx: int) -> Tuple[float, float]:
        """Simulasi pergerakan lurus ke arah Timur Laut"""
        # ~40 km/jam = ~11 m/s = ~0.0001 derajat per detik (approx)
        speed_factor = 0.00002  # Per frame pada 30fps
        
        lat = self.start_lat + (frame_idx * speed_factor * 0.5)
        lon = self.start_lon + (frame_idx * speed_factor * 0.8)
        
        return lat, lon
    
    def _get_interpolated_location(self, frame_idx: int, fps: float) -> Tuple[float, float]:
        """Interpolasi lokasi dari data GPS yang sudah di-load"""
        if not self.data:
            return self.start_lat, self.start_lon
        
        # Konversi frame ke detik
        current_time = frame_idx / fps
        
        # Cari 2 titik terdekat untuk interpolasi
        prev_point = self.data[0]
        next_point = self.data[-1]
        
        for i, point in enumerate(self.data):
            if point.timestamp >= current_time:
                next_point = point
                if i > 0:
                    prev_point = self.data[i-1]
                break
            prev_point = point
        
        # Jika sudah melewati data terakhir
        if current_time >= self.data[-1].timestamp:
            return self.data[-1].latitude, self.data[-1].longitude
        
        # Interpolasi linear
        if prev_point.timestamp == next_point.timestamp:
            return prev_point.latitude, prev_point.longitude
        
        t = (current_time - prev_point.timestamp) / (next_point.timestamp - prev_point.timestamp)
        t = max(0.0, min(1.0, t))  # Clamp ke [0, 1]
        
        lat = prev_point.latitude + t * (next_point.latitude - prev_point.latitude)
        lon = prev_point.longitude + t * (next_point.longitude - prev_point.longitude)
        
        return lat, lon
    
    def _get_manual_location(self, frame_idx: int) -> Tuple[float, float]:
        """Interpolasi linear dari start ke end"""
        if self.total_frames <= 0:
            return self.start_lat, self.start_lon
        
        t = min(1.0, frame_idx / self.total_frames)
        
        lat = self.start_lat + t * (self.end_lat - self.start_lat)
        lon = self.start_lon + t * (self.end_lon - self.start_lon)
        
        return lat, lon
    
    def haversine_distance(self, lat1: float, lon1: float, 
                          lat2: float, lon2: float) -> float:
        """Hitung jarak Haversine (dalam meter) antara dua titik"""
        R = 6371000  # Jari-jari bumi (meter)
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        
        return R * c
    
    def get_total_distance_km(self) -> float:
        """Dapatkan total jarak yang sudah ditempuh dalam km"""
        return self.total_distance_meters / 1000.0
    
    def reset(self):
        """Reset GPS manager ke kondisi awal"""
        self.last_lat = self.start_lat
        self.last_lon = self.start_lon
        self.total_distance_meters = 0.0
        self._prev_lat = self.start_lat
        self._prev_lon = self.start_lon
        self.realtime_lat = None
        self.realtime_lon = None
    
    def get_route_bounds(self) -> Tuple[float, float, float, float]:
        """
        Dapatkan bounding box dari rute.
        
        Returns:
            (min_lat, max_lat, min_lon, max_lon)
        """
        if self.data:
            lats = [p.latitude for p in self.data]
            lons = [p.longitude for p in self.data]
            return min(lats), max(lats), min(lons), max(lons)
        else:
            return (self.start_lat, self.end_lat, self.start_lon, self.end_lon)


def get_simulated_gps(frame_count: int, start_lat: float = -6.9175, 
                      start_lon: float = 107.6191) -> Tuple[float, float]:
    """
    Fungsi helper sederhana untuk simulasi GPS.
    Kompatibel dengan kode lama.
    """
    offset = frame_count * 0.00001
    return start_lat, start_lon + offset