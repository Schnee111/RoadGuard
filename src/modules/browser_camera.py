"""
Browser Camera Module for RoadGuard
Menggunakan streamlit-webrtc untuk akses kamera dari browser HP/Laptop.
Tidak perlu install app di HP - cukup buka di browser.
"""

import streamlit as st
import cv2
import numpy as np
from typing import Optional, Callable
import threading
import queue
import time

# Try import streamlit-webrtc
try:
    from streamlit_webrtc import webrtc_streamer, WebRtcMode, VideoProcessorBase
    import av
    HAS_WEBRTC = True
except ImportError:
    HAS_WEBRTC = False
    print("⚠️ streamlit-webrtc not installed. Run: pip install streamlit-webrtc av")


class FrameQueue:
    """Thread-safe queue untuk frame dari browser camera"""
    
    def __init__(self, maxsize: int = 5):
        self.queue = queue.Queue(maxsize=maxsize)
        self.latest_frame = None
        self.lock = threading.Lock()
    
    def put(self, frame):
        """Add frame ke queue"""
        with self.lock:
            self.latest_frame = frame
            try:
                # Non-blocking put, drop old frames jika penuh
                self.queue.put_nowait(frame)
            except queue.Full:
                try:
                    self.queue.get_nowait()
                    self.queue.put_nowait(frame)
                except:
                    pass
    
    def get(self, timeout: float = 0.1) -> Optional[np.ndarray]:
        """Get frame dari queue"""
        try:
            return self.queue.get(timeout=timeout)
        except queue.Empty:
            with self.lock:
                return self.latest_frame
    
    def get_latest(self) -> Optional[np.ndarray]:
        """Get frame terbaru (non-blocking)"""
        with self.lock:
            return self.latest_frame


# Global frame queue untuk sharing antar components
_frame_queue = FrameQueue()
_is_streaming = False


def get_frame_queue() -> FrameQueue:
    """Get global frame queue"""
    return _frame_queue


def is_browser_camera_active() -> bool:
    """Check apakah browser camera sedang aktif"""
    return _is_streaming


if HAS_WEBRTC:
    class RoadDamageProcessor(VideoProcessorBase):
        """
        Video processor untuk streamlit-webrtc.
        Menerima frame dari browser dan membuatnya available untuk processing.
        """
        
        def __init__(self):
            self.frame_queue = get_frame_queue()
            self.detection_callback = None
            self.annotated_frame = None
            self.lock = threading.Lock()
            global _is_streaming
            _is_streaming = True
        
        def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
            """
            Terima frame dari browser, proses, dan return untuk display.
            """
            # Convert ke numpy array (BGR)
            img = frame.to_ndarray(format="bgr24")
            
            # Put ke queue untuk processing di main thread
            self.frame_queue.put(img.copy())
            
            # Return frame untuk display (bisa sudah di-annotate)
            with self.lock:
                if self.annotated_frame is not None:
                    return av.VideoFrame.from_ndarray(self.annotated_frame, format="bgr24")
            
            return frame
        
        def set_annotated_frame(self, frame: np.ndarray):
            """Set annotated frame untuk display"""
            with self.lock:
                self.annotated_frame = frame
        
        def __del__(self):
            global _is_streaming
            _is_streaming = False


def render_browser_camera(key: str = "browser_cam"):
    """
    Render browser camera widget menggunakan streamlit-webrtc.
    
    Returns:
        webrtc_ctx: WebRTC context object, atau None jika tidak tersedia
    """
    if not HAS_WEBRTC:
        st.error("❌ streamlit-webrtc tidak terinstall!")
        st.code("pip install streamlit-webrtc av", language="bash")
        return None
    
    st.info("""
    📱 **Cara menggunakan kamera HP:**
    1. Buka URL aplikasi ini di browser HP (Chrome/Safari)
    2. Izinkan akses kamera saat diminta
    3. Klik START untuk mulai streaming
    
    💡 Pastikan HP dan laptop di jaringan WiFi yang sama!
    """)
    
    # WebRTC configuration
    rtc_configuration = {
        "iceServers": [
            {"urls": ["stun:stun.l.google.com:19302"]},
            {"urls": ["stun:stun1.l.google.com:19302"]},
        ]
    }
    
    # Media constraints - prefer rear camera di HP
    media_constraints = {
        "video": {
            "facingMode": {"ideal": "environment"},  # Rear camera
            "width": {"ideal": 1280},
            "height": {"ideal": 720},
            "frameRate": {"ideal": 15, "max": 30}
        },
        "audio": False
    }
    
    # Render webrtc streamer
    ctx = webrtc_streamer(
        key=key,
        mode=WebRtcMode.SENDRECV,
        rtc_configuration=rtc_configuration,
        media_stream_constraints=media_constraints,
        video_processor_factory=RoadDamageProcessor,
        async_processing=True,
    )
    
    return ctx


def render_simple_browser_camera(key: str = "simple_cam"):
    """
    Render versi simple dari browser camera.
    Hanya capture frame, tidak perlu processor.
    """
    if not HAS_WEBRTC:
        st.error("❌ streamlit-webrtc tidak terinstall!")
        return None
    
    from streamlit_webrtc import webrtc_streamer, WebRtcMode
    
    ctx = webrtc_streamer(
        key=key,
        mode=WebRtcMode.SENDONLY,  # Hanya kirim, tidak terima balik
        rtc_configuration={
            "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
        },
        media_stream_constraints={
            "video": {"facingMode": "environment"},
            "audio": False
        },
    )
    
    return ctx


def get_browser_frame() -> Optional[np.ndarray]:
    """
    Get frame terbaru dari browser camera.
    
    Returns:
        Frame sebagai numpy array (BGR), atau None jika tidak tersedia
    """
    return _frame_queue.get_latest()


def process_browser_camera_stream(
    detector,
    tracker,
    gps_manager,
    db,
    session_id: str,
    conf_thresh: float = 0.5,
    on_damage_detected: Optional[Callable] = None
):
    """
    Process stream dari browser camera.
    Ini dijalankan sebagai bagian dari main loop.
    
    Args:
        detector: RoadDamageDetector instance
        tracker: SpatialDamageTracker instance
        gps_manager: GPSManager instance
        db: DamageDatabase instance
        session_id: Current session ID
        conf_thresh: Confidence threshold
        on_damage_detected: Callback saat ada damage baru
    
    Returns:
        dict dengan stats dan deteksi
    """
    frame = get_browser_frame()
    
    if frame is None:
        return None
    
    # Run detection
    results = detector.model(frame, conf=conf_thresh, verbose=False)
    annotated_frame = results[0].plot()
    
    # Get GPS location
    curr_lat, curr_lon = gps_manager.get_realtime_location()
    
    # Process detections
    frame_detections = []
    if results[0].boxes:
        for box in results[0].boxes:
            xyxy = box.xyxy[0].tolist()
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            label = detector.model.names[cls_id]
            
            frame_detections.append({
                "bbox": xyxy,
                "type": label,
                "conf": conf
            })
    
    # Update tracker
    new_damages = tracker.update(frame_detections, (curr_lat, curr_lon))
    
    # Save new damages
    for dmg in new_damages:
        # Crop image
        x1, y1, x2, y2 = [int(c) for c in dmg['bbox']]
        x1, y1 = max(0, x1-20), max(0, y1-20)
        x2, y2 = min(annotated_frame.shape[1], x2+20), min(annotated_frame.shape[0], y2+20)
        cropped = annotated_frame[y1:y2, x1:x2]
        
        damage_data = {
            "track_id": dmg['track_id'],
            "timestamp": time.time(),
            "lat": dmg['lat'],
            "lon": dmg['lon'],
            "type": dmg['type'],
            "conf": dmg['conf'],
            "bbox": dmg['bbox'],
            "severity": "medium"
        }
        
        damage_id = db.insert_damage(damage_data, session_id, cropped)
        
        if on_damage_detected:
            on_damage_detected(damage_data)
    
    return {
        "frame": annotated_frame,
        "detections": frame_detections,
        "new_damages": new_damages,
        "location": (curr_lat, curr_lon)
    }
