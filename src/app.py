"""
RoadGuard Vision - AI-Powered Road Damage Detection System
Main Application Entry Point

Features:
- Multi-source video input (file, webcam, RTSP/IP camera)
- GPS integration (simulation, manual, GPX/CSV upload, REALTIME)
- IoU-based object tracking (anti-duplicate)
- SQLite database for persistent storage
- Interactive map with heatmap and filters
- Export to CSV, GeoJSON, KML, PDF
"""

import streamlit as st
import streamlit.components.v1 as components
import cv2
import os
import time
from datetime import datetime

# Import Modules
from modules.detector import RoadDamageDetector
from modules.gps_manager import GPSManager
from modules.bytetrack import ByteTracker as SpatialDamageTracker  # Using ByteTrack!
from modules.database import DamageDatabase, get_database
from modules.realtime_gps import render_realtime_gps, create_gps_component_html, get_realtime_gps

# Browser Camera (optional - untuk HP)
try:
    from modules.browser_camera import (
        render_browser_camera, 
        get_browser_frame, 
        is_browser_camera_active,
        HAS_WEBRTC
    )
except ImportError:
    HAS_WEBRTC = False

# Import Components
from components.styling import load_css
from components.sidebar import render_sidebar, render_history_view
from components.dashboard import (
    render_stats_panel, 
    render_video_container, 
    render_progress_bar,
    render_session_summary
)
from components.map_view import (
    render_live_map_container, 
    update_live_map, 
    render_analysis_map,
    render_history_map
)
from components.export import render_export_buttons


# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="RoadGuard Vision", 
    layout="wide", 
    page_icon="🛡️",
    initial_sidebar_state="expanded"
)
load_css()


# ==========================================
# 2. STATE MANAGEMENT
# ==========================================
def init_session_state():
    """Initialize all session state variables"""
    defaults = {
        'detections': [],
        'is_running': False,
        'session_id': None,
        'view_mode': 'inspection',  # 'inspection' or 'history'
        'tracker_iou': 0.3,
        'tracker_min_hits': 2,
        'min_distance': 5.0,
        'view_session': None,
        'export_session': None,
        'realtime_gps_main': None,  # For realtime GPS data
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()


# ==========================================
# 3. DATABASE INITIALIZATION
# ==========================================
@st.cache_resource
def get_db():
    """Get database instance (cached)"""
    return get_database("results/roadguard.db")

db = get_db()


# ==========================================
# 4. HEADER
# ==========================================
st.markdown('<div class="header-title">🛡️ RoadGuard Vision</div>', unsafe_allow_html=True)
st.markdown('<div class="header-subtitle">AI-Powered Road Damage Detection & Geotagging System</div>', unsafe_allow_html=True)


# ==========================================
# 5. SIDEBAR
# ==========================================
sidebar_result = render_sidebar()
start_btn, stop_btn, reset_btn, video_path, conf_thresh, gps_config, view_history_btn = sidebar_result


# ==========================================
# 6. REALTIME GPS WIDGET (if mode is realtime)
# ==========================================
if gps_config.get('mode') == 'realtime':
    with st.sidebar:
        st.markdown("### 📍 GPS Status")
        # Render GPS widget di sidebar
        gps_html = create_gps_component_html("main")
        components.html(gps_html, height=200, scrolling=False)


# ==========================================
# 7. BUTTON LOGIC
# ==========================================
if start_btn and video_path is not None:
    st.session_state['is_running'] = True
    st.session_state['view_mode'] = 'inspection'
    
if stop_btn:
    st.session_state['is_running'] = False
    
if reset_btn:
    st.session_state['detections'] = []
    st.session_state['is_running'] = False
    st.session_state['session_id'] = None
    st.rerun()
    
if view_history_btn:
    st.session_state['view_mode'] = 'history'
    st.session_state['is_running'] = False


# ==========================================
# 8. HISTORY VIEW MODE
# ==========================================
if st.session_state['view_mode'] == 'history':
    render_history_view(db)
    
    # Handle view specific session - MAP VIEW
    if st.session_state.get('view_session') and st.session_state.get('action_pending') == 'view_map':
        st.markdown("---")
        st.markdown("### 📍 Session Map & Details")
        
        session_id = st.session_state['view_session']
        records = db.get_damages_by_session(session_id)
        
        # Get session info for video path
        sessions = db.get_all_sessions()
        session_info = next((s for s in sessions if s['id'] == session_id), None)
        video_path_history = session_info.get('video_path') if session_info else None
        
        if records or video_path_history:
            # Show processed video with bounding boxes (if available)
            if video_path_history and os.path.exists(video_path_history):
                st.markdown("#### 🎬 Full Video with Bounding Boxes")
                st.video(video_path_history)
                st.caption(f"📁 Video path: {video_path_history}")
            
            if records:
                st.markdown("#### 🖼️ Detected Damages Gallery")
                
                # View mode selection
                view_mode_choice = st.radio(
                    "Display Mode",
                    ["Grid View", "Slideshow"],
                    horizontal=True,
                    label_visibility="collapsed"
                )
            
            if view_mode_choice == "Grid View":
                # Display images in grid
                cols_per_row = 3
                for i in range(0, len(records), cols_per_row):
                    cols = st.columns(cols_per_row)
                    for j, col in enumerate(cols):
                        if i + j < len(records):
                            record = records[i + j]
                            with col:
                                if record.image_path and os.path.exists(record.image_path):
                                    st.image(record.image_path, use_container_width=True)
                                    st.markdown(f"**{record.damage_type}**")
                                    
                                    # Info badges
                                    severity_color = {
                                        'high': '🔴',
                                        'medium': '🟠', 
                                        'low': '🟢'
                                    }.get(record.severity, '⚪')
                                    
                                    st.caption(f"{severity_color} {record.severity.upper()} | Conf: {record.confidence:.1%}")
                                    st.caption(f"📍 {record.latitude:.6f}, {record.longitude:.6f}")
                                    st.caption(f"⏱️ {record.timestamp:.1f}s")
                                else:
                                    st.warning("Image not available")
            else:
                # Slideshow mode
                if 'slideshow_index' not in st.session_state:
                    st.session_state['slideshow_index'] = 0
                
                idx = st.session_state['slideshow_index']
                record = records[idx]
                
                # Display current image
                col1, col2, col3 = st.columns([1, 3, 1])
                
                with col2:
                    if record.image_path and os.path.exists(record.image_path):
                        st.image(record.image_path, use_container_width=True)
                    else:
                        st.warning("Image not available")
                    
                    # Info
                    st.markdown(f"### {record.damage_type}")
                    
                    severity_emoji = {
                        'high': '🔴',
                        'medium': '🟠',
                        'low': '🟢'
                    }.get(record.severity, '⚪')
                    
                    col_a, col_b, col_c = st.columns(3)
                    col_a.metric("Severity", f"{severity_emoji} {record.severity.upper()}")
                    col_b.metric("Confidence", f"{record.confidence:.1%}")
                    col_c.metric("Time", f"{record.timestamp:.1f}s")
                    
                    st.markdown(f"**Location:** {record.latitude:.6f}, {record.longitude:.6f}")
                
                # Navigation
                col_prev, col_info, col_next = st.columns([1, 2, 1])
                
                with col_prev:
                    if st.button("⬅️ Previous", disabled=(idx == 0)):
                        st.session_state['slideshow_index'] -= 1
                        st.rerun()
                
                with col_info:
                    st.markdown(f"<center>{idx + 1} / {len(records)}</center>", unsafe_allow_html=True)
                
                with col_next:
                    if st.button("Next ➡️", disabled=(idx == len(records) - 1)):
                        st.session_state['slideshow_index'] += 1
                        st.rerun()
            
            if records:
                st.markdown("---")
                
                # Show map
                st.markdown("#### 🗺️ Damage Locations Map")
                render_history_map(db, session_id)
        else:
            st.warning("No damage records or video found for this session.")
        
        # Clear action
        if st.button("✖️ Close Details"):
            st.session_state['view_session'] = None
            st.session_state['action_pending'] = None
            st.rerun()
    
    # Handle export
    elif st.session_state.get('export_session') and st.session_state.get('action_pending') == 'export':
        st.markdown("---")
        st.markdown("### 📥 Export Session Data")
        
        session_id = st.session_state['export_session']
        records = db.get_damages_by_session(session_id)
        
        if records:
            detections = [
                {
                    'lat': r.latitude, 'lon': r.longitude, 'type': r.damage_type,
                    'timestamp': r.timestamp, 'conf': r.confidence, 'severity': r.severity,
                    'image_path': r.image_path
                }
                for r in records
            ]
            render_export_buttons(detections, db, session_id)
        else:
            st.warning("No data to export.")
        
        # Clear action
        if st.button("✖️ Close Export"):
            st.session_state['export_session'] = None
            st.session_state['action_pending'] = None
            st.rerun()
    
    # Back button (only show if no action pending)
    if not st.session_state.get('action_pending'):
        if st.button("⬅️ Back to Inspection"):
            st.session_state['view_mode'] = 'inspection'
            st.rerun()
    
    st.stop()


# ==========================================
# 9. MAIN INSPECTION LAYOUT
# ==========================================
col_left, col_right = st.columns([1.8, 1])

with col_left:
    video_placeholder = render_video_container()
    progress_placeholder = st.empty()

with col_right:
    # Show GPS widget in main area if realtime mode
    if gps_config.get('mode') == 'realtime':
        gps_status_placeholder = st.empty()
        with gps_status_placeholder.container():
            st.markdown("#### 📍 Live GPS Tracking")
            gps_html = create_gps_component_html("display")
            components.html(gps_html, height=180, scrolling=False)
    
    map_placeholder = render_live_map_container()
    stats_placeholder = st.empty()


# ==========================================
# 10. VIDEO PROCESSING
# ==========================================

# Check if using browser camera
use_browser_camera = st.session_state.get('use_browser_camera', False)

if use_browser_camera:
    # ==========================================
    # BROWSER CAMERA MODE (HP/Laptop)
    # ==========================================
    st.markdown("### 📱 Browser Camera")
    st.info("Izinkan akses kamera saat browser meminta. Kamera HP akan otomatis menggunakan kamera belakang.")
    
    if not HAS_WEBRTC:
        st.error("❌ Library streamlit-webrtc tidak tersedia!")
        st.code("pip install streamlit-webrtc av", language="bash")
        webrtc_ctx = None
    else:
        # Render browser camera widget
        webrtc_ctx = render_browser_camera("main_camera")
    
    if webrtc_ctx and webrtc_ctx.state.playing:
        st.success("📹 Camera is streaming! Processing frames...")
        
        # Initialize components jika belum
        if 'browser_cam_initialized' not in st.session_state:
            # Initialize detector
            model_path = 'src/models/YOLOv8_Small_RDD.pt'
            if not os.path.exists(model_path):
                model_path = 'models/YOLOv8_Small_RDD.pt'
            
            st.session_state['browser_detector'] = RoadDamageDetector(model_path=model_path)
            st.session_state['browser_tracker'] = SpatialDamageTracker(
                high_thresh=st.session_state.get('tracker_high_thresh', 0.3),
                low_thresh=st.session_state.get('tracker_low_thresh', 0.1),
                match_thresh=st.session_state.get('tracker_iou', 0.3),
                max_age=st.session_state.get('tracker_max_age', 30),
                min_hits=1,
                min_distance_meters=st.session_state.get('min_distance', 10.0)
            )
            st.session_state['browser_gps'] = GPSManager(mode=gps_config.get('mode', 'simulation'))
            st.session_state['browser_session'] = db.create_session("browser_camera")
            st.session_state['browser_cam_initialized'] = True
        
        # Get latest frame and process
        frame = get_browser_frame()
        if frame is not None:
            detector = st.session_state['browser_detector']
            tracker = st.session_state['browser_tracker']
            gps_manager = st.session_state['browser_gps']
            session_id = st.session_state['browser_session']
            
            # Run detection
            results = detector.model(frame, conf=conf_thresh, verbose=False)
            annotated_frame = results[0].plot()
            
            # Display frame
            frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
            video_placeholder.image(frame_rgb, channels="RGB", use_container_width=True)
            
            # Get GPS
            if gps_config['mode'] == 'realtime':
                curr_lat, curr_lon = gps_manager.get_realtime_location()
            else:
                curr_lat, curr_lon = gps_manager.get_location_at_frame(0, 30)
            
            # Process detections
            if results[0].boxes:
                frame_detections = []
                for box in results[0].boxes:
                    xyxy = box.xyxy[0].tolist()
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    label = detector.model.names[cls_id]
                    frame_detections.append({"bbox": xyxy, "type": label, "conf": conf})
                
                new_damages = tracker.update(frame_detections, (curr_lat, curr_lon))
                
                for dmg in new_damages:
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
                        "severity": "medium",
                        "image_path": None
                    }
                    
                    damage_id = db.insert_damage(damage_data, session_id, cropped)
                    if damage_id:
                        record = db.get_damage_by_id(damage_id)
                        if record:
                            damage_data['image_path'] = record.image_path
                    
                    st.session_state['detections'].append(damage_data)
            
            # Update stats
            with stats_placeholder.container():
                render_stats_panel(st.session_state['detections'], tracker_stats={'active_tracks': len(tracker.tracks)})
            
            # Update map
            update_live_map(map_placeholder, st.session_state['detections'])
    
    elif webrtc_ctx:
        st.info("👆 Click **START** to begin camera streaming")

elif st.session_state['is_running'] and video_path is not None and video_path != "BROWSER_CAMERA":
    
    # ----- INITIALIZATION -----
    
    # Initialize detector
    model_path = 'src/models/YOLOv8_Small_RDD.pt'
    if not os.path.exists(model_path):
        model_path = 'models/YOLOv8_Small_RDD.pt'
    
    try:
        detector = RoadDamageDetector(model_path=model_path)
    except Exception as e:
        st.error(f"❌ Failed to load model: {e}")
        st.session_state['is_running'] = False
        st.stop()
    
    # Initialize GPS Manager
    gps_manager = GPSManager(
        mode=gps_config.get('mode', 'simulation'),
        start_lat=gps_config.get('start_lat', -6.9024),
        start_lon=gps_config.get('start_lon', 107.6188)
    )
    
    # Configure GPS based on mode
    if gps_config['mode'] == 'realtime':
        gps_manager.set_realtime_mode('realtime_gps_main')
        st.info("📍 GPS Realtime Mode: Lokasi diambil dari browser Anda")
        
    elif gps_config.get('file_path'):
        if gps_config['mode'] == 'gpx':
            gps_manager.load_gpx(gps_config['file_path'])
        elif gps_config['mode'] == 'csv':
            gps_manager.load_csv(gps_config['file_path'])
    
    # Set manual route if applicable
    if gps_config['mode'] == 'manual':
        # Get total frames first (need to open video briefly)
        temp_cap = cv2.VideoCapture(video_path)
        total_frames = int(temp_cap.get(cv2.CAP_PROP_FRAME_COUNT))
        temp_cap.release()
        
        gps_manager.set_manual_route(
            start_lat=gps_config['start_lat'],
            start_lon=gps_config['start_lon'],
            end_lat=gps_config['end_lat'],
            end_lon=gps_config['end_lon'],
            total_frames=total_frames
        )
    
    # Initialize ByteTracker (SOTA tracking algorithm)
    tracker = SpatialDamageTracker(
        high_thresh=st.session_state.get('tracker_high_thresh', 0.3),  # High confidence threshold
        low_thresh=st.session_state.get('tracker_low_thresh', 0.1),   # Low confidence threshold
        match_thresh=st.session_state.get('tracker_iou', 0.3),        # IoU threshold
        max_age=st.session_state.get('tracker_max_age', 30),          # Track persistence
        min_hits=1,  # Langsung simpan
        min_distance_meters=st.session_state.get('min_distance', 10.0)
    )
    
    # Set spatial dedup flag
    tracker.enable_spatial_dedup = st.session_state.get('enable_spatial_dedup', True)
    
    # Create session
    video_source_str = str(video_path) if not isinstance(video_path, int) else f"Webcam {video_path}"
    session_id = db.create_session(video_source=video_source_str)
    st.session_state['session_id'] = session_id
    
    # Open video
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        st.error(f"❌ Cannot open video source: {video_path}")
        st.session_state['is_running'] = False
        st.stop()
    
    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # For webcam/stream, total_frames might be 0
    is_stream = total_frames <= 0
    
    # Initialize Video Writer to save processed video with bounding boxes
    output_video_path = None
    temp_video_path = None
    video_writer = None
    if not is_stream:  # Only save for file-based videos
        os.makedirs("results/videos", exist_ok=True)
        output_video_path = f"results/videos/{session_id}.mp4"
        temp_video_path = f"results/videos/{session_id}_temp.avi"
        # Use AVI format with XVID codec (more compatible for writing)
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        video_writer = cv2.VideoWriter(temp_video_path, fourcc, fps, (frame_width, frame_height))
        print(f"📹 Video writer initialized: {temp_video_path}")
    
    frame_count = 0
    last_map_update = 0
    MAP_UPDATE_INTERVAL = 15  # Update map every N frames
    
    # Frame skipping settings
    INFERENCE_INTERVAL = st.session_state.get('inference_interval', 1)
    UI_UPDATE_INTERVAL = st.session_state.get('ui_update_interval', 2)
    last_inference_frame = 0
    last_detection_results = None
    last_annotated_frame = None
    
    # ----- MAIN PROCESSING LOOP -----
    
    try:
        while cap.isOpened() and st.session_state['is_running']:
            ret, frame = cap.read()
            
            if not ret:
                if is_stream:
                    # For streams, try to reconnect
                    time.sleep(0.1)
                    continue
                else:
                    break
            
            frame_count += 1
            
            # ----- 1. DETECTION (OPTIMIZED - Skip frames) -----
            if frame_count - last_inference_frame >= INFERENCE_INTERVAL:
                results = detector.model(frame, conf=conf_thresh, verbose=False)
                last_detection_results = results
                last_annotated_frame = results[0].plot()
                annotated_frame = last_annotated_frame
                last_inference_frame = frame_count
            else:
                # Use previous detection result
                results = last_detection_results
                if last_annotated_frame is not None:
                    annotated_frame = last_annotated_frame
                else:
                    annotated_frame = frame
            
            # ----- 2. GPS (OPTIMIZED - Cache untuk file-based video) -----
            if gps_config['mode'] == 'realtime':
                # Realtime GPS tidak bisa di-cache, harus setiap frame
                curr_lat, curr_lon = gps_manager.get_location_at_frame(frame_count, fps)
            else:
                # File-based GPS bisa di-cache
                curr_lat, curr_lon = gps_manager.get_location_at_frame(frame_count, fps)
            
            # ----- 3. TRACKING (Only when we have new detections) -----
            frame_detections = []
            new_damages = []
            
            if results and results[0].boxes and frame_count == last_inference_frame:
                print(f"\n🔍 Frame {frame_count}: Found {len(results[0].boxes)} detections")
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
                    print(f"  - {label} (conf: {conf:.2f})")
                
                print(f"📍 GPS: ({curr_lat:.6f}, {curr_lon:.6f})")
                
                # Update tracker - returns only NEW unique damages
                new_damages = tracker.update(frame_detections, (curr_lat, curr_lon))
                
                if new_damages:
                    print(f"✨ Tracker returned {len(new_damages)} NEW damages")
                    for dmg in new_damages:
                        print(f"  - Track ID {dmg['track_id']}: {dmg['type']}")
                else:
                    print("⚠️ Tracker returned 0 new damages (might be duplicates)")
            
            # ----- 4. SAVE NEW DAMAGES (OPTIMIZED - Batch insert) -----
            if new_damages:
                print(f"\n💾 Saving {len(new_damages)} damages to database...")
                for dmg in new_damages:
                    try:
                        print(f"  Processing damage: {dmg['type']} at ({dmg['lat']:.6f}, {dmg['lon']:.6f})")
                        # Determine severity
                        severity = "medium"
                        if "pothole" in dmg['type'].lower() or "d40" in dmg['type'].lower():
                            severity = "high" if dmg['conf'] > 0.6 else "medium"
                        elif "alligator" in dmg['type'].lower() or "d20" in dmg['type'].lower():
                            severity = "high" if dmg['conf'] > 0.7 else "medium"
                        elif dmg['conf'] < 0.4:
                            severity = "low"
                        
                        # Crop image dengan bounding box (dari annotated frame)
                        # Ini akan include bounding box dan label di gambar
                        x1, y1, x2, y2 = [int(c) for c in dmg['bbox']]
                        x1, y1 = max(0, x1-20), max(0, y1-20)
                        x2, y2 = min(annotated_frame.shape[1], x2+20), min(annotated_frame.shape[0], y2+20)
                        cropped_with_bbox = annotated_frame[y1:y2, x1:x2]
                        
                        # Prepare data
                        damage_data = {
                            "track_id": dmg['track_id'],
                            "timestamp": frame_count / fps,
                            "lat": dmg['lat'],
                            "lon": dmg['lon'],
                            "type": dmg['type'],
                            "conf": dmg['conf'],
                            "bbox": dmg['bbox'],
                            "severity": severity,
                            "image_path": None
                        }
                        
                        # Save to database dan dapatkan image_path
                        damage_id = db.insert_damage(damage_data, session_id, cropped_with_bbox)
                        
                        # Update dengan image_path dari database
                        if damage_id:
                            record = db.get_damage_by_id(damage_id)
                            if record and record.image_path:
                                damage_data['image_path'] = record.image_path
                                print(f"✅ Damage {damage_id} saved with image: {record.image_path}")
                            else:
                                print(f"⚠️ Damage {damage_id} saved but no image path")
                        else:
                            print(f"❌ Failed to save damage to database")
                        
                        # Add to session state (dengan image_path)
                        st.session_state['detections'].append(damage_data)
                        
                    except Exception as e:
                        # Log error tapi lanjutkan processing
                        print(f"Error saving damage: {e}")
                        continue
            
            # ----- 5. WRITE TO OUTPUT VIDEO -----
            if video_writer is not None:
                video_writer.write(annotated_frame)
            
            # ----- 6. UPDATE UI (OPTIMIZED - Throttled) -----
            
            # Video feed (only every N frames untuk reduce Streamlit overhead)
            if frame_count % UI_UPDATE_INTERVAL == 0:
                frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
                
                # OPTIMIZED: Resize untuk display - BACA DARI SIDEBAR SETTINGS
                display_width = st.session_state.get('display_width', 800)
                if frame_rgb.shape[1] > display_width:
                    scale = display_width / frame_rgb.shape[1]
                    new_height = int(frame_rgb.shape[0] * scale)
                    frame_rgb = cv2.resize(frame_rgb, (display_width, new_height))
                
                video_placeholder.image(frame_rgb, channels="RGB", width='stretch')
            
            # Progress bar
            if not is_stream and total_frames > 0 and frame_count % 10 == 0:
                with progress_placeholder:
                    render_progress_bar(frame_count, total_frames, fps)
            
            # Map (update lebih jarang)
            if frame_count - last_map_update >= MAP_UPDATE_INTERVAL:
                update_live_map(map_placeholder, st.session_state['detections'])
                last_map_update = frame_count
            
            # Stats (update hanya saat ada perubahan)
            if new_damages or frame_count % 30 == 0:
                with stats_placeholder.container():
                    render_stats_panel(
                        st.session_state['detections'],
                        tracker_stats={
                            'active_tracks': len(tracker.tracks),
                            'frames_processed': frame_count
                        }
                    )
            
            # OPTIMIZED: Allow graceful stop
            if not st.session_state.get('is_running', False):
                break
    
    except Exception as e:
        st.error(f"⚠️ Processing error: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        # Don't break, just log the error
    
    finally:
        cap.release()
        
        # Release video writer and convert to browser-compatible format
        if video_writer is not None:
            video_writer.release()
            print(f"📹 Temp video saved: {temp_video_path}")
            
            # Convert to H.264 MP4 for browser compatibility using ffmpeg
            if temp_video_path and os.path.exists(temp_video_path):
                try:
                    import subprocess
                    # Use ffmpeg to convert to H.264 codec (browser compatible)
                    ffmpeg_cmd = [
                        'ffmpeg', '-y', '-i', temp_video_path,
                        '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
                        '-pix_fmt', 'yuv420p',  # Required for browser compatibility
                        output_video_path
                    ]
                    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=300)
                    
                    if result.returncode == 0:
                        print(f"✅ Video converted to H.264: {output_video_path}")
                        # Remove temp file
                        os.remove(temp_video_path)
                    else:
                        print(f"⚠️ FFmpeg conversion failed: {result.stderr}")
                        # Fallback: rename temp as output
                        import shutil
                        shutil.move(temp_video_path, output_video_path)
                except FileNotFoundError:
                    print("⚠️ FFmpeg not found, using original video (may not play in browser)")
                    import shutil
                    shutil.move(temp_video_path, output_video_path)
                except Exception as e:
                    print(f"⚠️ Video conversion error: {e}")
                    import shutil
                    shutil.move(temp_video_path, output_video_path)
        
        # End session with video path
        db.end_session(session_id, gps_manager.get_total_distance_km(), output_video_path)
        
        st.session_state['is_running'] = False
        
        # Show completion message
        st.success(f"✅ Inspection Complete! Found {len(st.session_state['detections'])} unique damages.")
        if output_video_path and os.path.exists(output_video_path):
            st.info(f"📹 Processed video saved: {output_video_path}")


# ==========================================
# 11. RESULTS SECTION (Always visible)
# ==========================================
st.markdown("---")

if st.session_state['detections']:
    # Tab layout for different views
    tab1, tab2, tab3 = st.tabs(["📍 Map Analysis", "📊 Summary", "📥 Export"])
    
    with tab1:
        render_analysis_map(st.session_state['detections'])
    
    with tab2:
        render_session_summary(
            st.session_state['detections'],
            gps_manager=None,  # Will use data from detections
            db=db,
            session_id=st.session_state.get('session_id')
        )
    
    with tab3:
        render_export_buttons(
            st.session_state['detections'],
            db,
            st.session_state.get('session_id')
        )

else:
    st.info("""
    👋 **Welcome to RoadGuard Vision!**
    
    Get started:
    1. Select a video source in the sidebar
    2. Configure GPS settings (or use simulation)
    3. Adjust AI sensitivity if needed
    4. Click **START** to begin inspection
    
    💡 **Tips:**
    - Use **Realtime GPS** mode when using webcam/IP camera for live inspection
    - Upload GPX file from your GPS tracker for accurate location
    - Check the **HISTORY** button to view past inspections
    """)


# ==========================================
# 12. FOOTER
# ==========================================
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888; font-size: 0.8rem;">
    RoadGuard Vision v2.0 | AI-Powered Road Damage Detection System<br>
    Built with ❤️ using Streamlit, YOLOv8, and OpenCV
</div>
""", unsafe_allow_html=True)