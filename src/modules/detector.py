"""
Road Damage Detector Module
Menggunakan YOLOv8 untuk deteksi kerusakan jalan.
"""

import cv2
import time
import os
from ultralytics import YOLO
from typing import List, Dict, Tuple, Optional


# Label mapping dari kode RDD ke nama yang mudah dibaca
LABEL_MAP = {
    "D00": "Longitudinal Crack",
    "D10": "Transverse Crack", 
    "D20": "Alligator Crack",
    "D40": "Pothole",
    "D43": "Damaged Lane Marking",
    "D44": "Faded Lane Marking",
    # Fallback untuk model lain
    "pothole": "Pothole",
    "crack": "Crack",
    "longitudinal": "Longitudinal Crack",
    "transverse": "Transverse Crack",
    "alligator": "Alligator Crack"
}


class RoadDamageDetector:
    """
    Detector untuk kerusakan jalan menggunakan YOLOv8.
    
    Mendukung model:
    - YOLOv8 yang ditraining pada dataset RDD (Road Damage Detection)
    
    Attributes:
        model: YOLO model instance
        label_map: Dictionary untuk mapping label
        confidence_threshold: Default confidence threshold
    """
    
    def __init__(self, model_path: str = None, confidence_threshold: float = 0.35):
        """
        Initialize detector.
        
        Args:
            model_path: Path ke file model .pt
            confidence_threshold: Minimum confidence untuk deteksi
        """
        self.confidence_threshold = confidence_threshold
        self.label_map = LABEL_MAP.copy()
        
        # Cari model path
        if model_path and os.path.exists(model_path):
            self.model_path = model_path
        else:
            # Coba beberapa lokasi
            possible_paths = [
                'src/models/YOLOv8_Small_RDD.pt'
            ]
            self.model_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    self.model_path = path
                    break
            
            if self.model_path is None:
                raise FileNotFoundError(
                    f"Model not found. Tried: {possible_paths}"
                )
        
        # Load model
        self.model = YOLO(self.model_path)
        
        # Update label map dengan nama dari model
        self._update_label_map()
    
    def _update_label_map(self):
        """Update label map berdasarkan kelas dari model"""
        for idx, name in self.model.names.items():
            if name not in self.label_map:
                # Coba map berdasarkan pattern
                name_lower = name.lower()
                if 'd00' in name_lower or 'longitudinal' in name_lower:
                    self.label_map[name] = "Longitudinal Crack"
                elif 'd10' in name_lower or 'transverse' in name_lower:
                    self.label_map[name] = "Transverse Crack"
                elif 'd20' in name_lower or 'alligator' in name_lower:
                    self.label_map[name] = "Alligator Crack"
                elif 'd40' in name_lower or 'pothole' in name_lower:
                    self.label_map[name] = "Pothole"
    
    def get_readable_label(self, raw_label: str) -> str:
        """Convert raw label ke human-readable label"""
        return self.label_map.get(raw_label, raw_label)
    
    def detect(self, frame, confidence: float = None) -> List[Dict]:
        """
        Detect damages in a single frame.
        
        Args:
            frame: OpenCV image (BGR)
            confidence: Override confidence threshold
            
        Returns:
            List of detections with keys:
            - bbox: [x1, y1, x2, y2]
            - type: damage type label
            - conf: confidence score
            - raw_label: original model label
        """
        conf = confidence or self.confidence_threshold
        
        results = self.model(frame, conf=conf, verbose=False)
        
        detections = []
        
        if results[0].boxes:
            for box in results[0].boxes:
                xyxy = box.xyxy[0].tolist()
                cls_id = int(box.cls[0])
                conf_score = float(box.conf[0])
                raw_label = self.model.names[cls_id]
                
                detections.append({
                    "bbox": xyxy,
                    "type": self.get_readable_label(raw_label),
                    "conf": conf_score,
                    "raw_label": raw_label,
                    "class_id": cls_id
                })
        
        return detections
    
    def detect_and_annotate(self, frame, confidence: float = None) -> Tuple:
        """
        Detect damages and return annotated frame.
        
        Args:
            frame: OpenCV image (BGR)
            confidence: Override confidence threshold
            
        Returns:
            (annotated_frame, detections_list)
        """
        conf = confidence or self.confidence_threshold
        
        results = self.model(frame, conf=conf, verbose=False)
        annotated_frame = results[0].plot()
        
        detections = []
        
        if results[0].boxes:
            for box in results[0].boxes:
                xyxy = box.xyxy[0].tolist()
                cls_id = int(box.cls[0])
                conf_score = float(box.conf[0])
                raw_label = self.model.names[cls_id]
                
                detections.append({
                    "bbox": xyxy,
                    "type": self.get_readable_label(raw_label),
                    "conf": conf_score,
                    "raw_label": raw_label,
                    "class_id": cls_id
                })
        
        return annotated_frame, detections
    
    def process_video(self, video_path: str, callback=None):
        """
        Process video file frame by frame.
        
        Args:
            video_path: Path to video file
            callback: Optional callback function(frame, detections, frame_idx)
            
        Yields:
            (annotated_frame_rgb, detections, frame_idx)
        """
        cap = cv2.VideoCapture(video_path)
        frame_idx = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_idx += 1
            
            # Detect and annotate
            annotated_frame, detections = self.detect_and_annotate(frame)
            
            # Convert to RGB for display
            rgb_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
            
            if callback:
                callback(frame, detections, frame_idx)
            
            yield rgb_frame, detections, frame_idx
        
        cap.release()
    
    def get_model_info(self) -> Dict:
        """Get information about the loaded model"""
        return {
            "model_path": self.model_path,
            "classes": list(self.model.names.values()),
            "num_classes": len(self.model.names),
            "confidence_threshold": self.confidence_threshold
        }


# Utility functions for standalone usage
def load_detector(model_path: str = None) -> RoadDamageDetector:
    """Convenience function to load detector"""
    return RoadDamageDetector(model_path)