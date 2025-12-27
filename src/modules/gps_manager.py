# File: modules/gps_manager.py
import pandas as pd
import numpy as np
from math import radians, cos, sin, asin, sqrt

class GPSManager:
    def __init__(self, csv_path=None):
        self.data = None
        if csv_path:
            # Asumsi CSV punya kolom: timestamp, latitude, longitude
            self.data = pd.read_csv(csv_path)
            # Pastikan format waktu/index sesuai kebutuhan
        
        # Koordinat Demo (Gedung Sate Bandung)
        self.last_lat = -6.9024
        self.last_lon = 107.6188

    def get_location_at_frame(self, frame_idx, fps=30):
        """
        Mengambil lokasi berdasarkan waktu video.
        Jika ada file CSV real, ambil dari situ.
        Jika tidak, lakukan simulasi yang lebih halus (interpolasi).
        """
        if self.data is not None:
            # LOGIKA REAL: Ambil baris yang sesuai dengan detik video
            seconds = frame_idx / fps
            # Implementasi pembacaan real CSV disini (butuh format data yang pasti)
            # Untuk sekarang kita skip agar tidak error tanpa file
            pass
            
        # LOGIKA SIMULASI HALUS (Jalan lurus ke arah Timur Laut)
        # Kita buat pergerakan lebih natural, tidak patah-patah
        speed_factor = 0.00002 # Kecepatan per frame
        self.last_lat += speed_factor * 0.5 
        self.last_lon += speed_factor * 0.8
        
        return self.last_lat, self.last_lon

    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """Hitung jarak Haversine (dalam meter) antara dua titik"""
        R = 6371000 # Jari-jari bumi (meter)
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        return R * c