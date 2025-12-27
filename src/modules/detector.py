import cv2
import time
from ultralytics import YOLO

class RoadDamageDetector:
    def __init__(self, model_path=None):
        # Jika tidak ada path khusus, gunakan model RDD yang baru didownload
        if model_path:
            self.model = YOLO(model_path)
        else:
            # GANTI string ini sesuai nama file Anda
            self.model = YOLO('models/YOLOv8_small_RDD.pt') 
            
    def process_video(self, video_path):
        cap = cv2.VideoCapture(video_path)
        
        # Simulasi GPS (Start: Gedung Sate)
        lat = -6.9024
        lon = 107.6188
        
        # KAMUS PENERJEMAH KODE RDD (PENTING!)
        # Model RDD outputnya adalah D00, D10, dst. Kita ubah jadi Bahasa Indonesia.
        label_map = {
            "D00": "Retak Memanjang (Longitudinal)",
            "D10": "Retak Melintang (Transverse)",
            "D20": "Retak Buaya (Alligator Crack)",
            "D40": "Lubang (Pothole)", # Ini target utama
            "D43": "Marka Rusak",
            "D44": "Marka Pudar"
        }
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # Deteksi (Confidence > 0.25 agar lebih sensitif menangkap lubang)
            results = self.model(frame, conf=0.25)
            
            # Gambar kotak hasil deteksi
            annotated_frame = results[0].plot()
            
            detections = []
            if results[0].boxes:
                # Simulasi pergerakan mobil
                lon += 0.00005 
                lat += 0.00001
                
                for box in results[0].boxes:
                    cls_id = int(box.cls[0])
                    raw_name = self.model.names[cls_id] # Contoh output: "D40"
                    conf = float(box.conf[0])
                    
                    # Terjemahkan kode D40 menjadi "Lubang"
                    readable_name = label_map.get(raw_name, raw_name)
                    
                    detections.append({
                        "Timestamp": time.strftime("%H:%M:%S"),
                        "Latitude": lat,
                        "Longitude": lon,
                        "Jenis Kerusakan": readable_name, # Pakai nama manusia
                        "Confidence": f"{conf:.2f}",
                        "Raw_Label": raw_name
                    })
            
            # Konversi warna BGR -> RGB untuk Streamlit
            rgb_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
            
            yield rgb_frame, detections, lat, lon

        cap.release()