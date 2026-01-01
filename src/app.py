"""
RoadGuard Vision - AI-Powered Road Damage Detection System
Main Application Entry Point

Features:
- Multi-source video input (file, webcam, RTSP/IP camera)
- GPS integration (simulation, manual, GPX/CSV upload)
- IoU-based object tracking (anti-duplicate)
- SQLite database for persistent storage
- Interactive map with heatmap and filters
- Export to CSV, GeoJSON, KML, PDF
"""

import streamlit as st
import cv2
import os
import time
from datetime import datetime

# Import Modules
from modules.detector import RoadDamageDetector
from modules.gps_manager import GPSManager
from modules.tracker import SpatialDamageTracker
from modules.database import DamageDatabase, get_database

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
        'export_session': None
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
# 6. BUTTON LOGIC
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
# 7. HISTORY VIEW MODE
# ==========================================
if st.session_state['view_mode'] == 'history':
    render_history_view(db)
    
    # Handle view specific session
    if st.session_state.get('view_session'):
        st.markdown("---")
        render_history_map(db, st.session_state['view_session'])
        st.session_state['view_session'] = None
    
    # Handle export
    if st.session_state.get('export_session'):
        records = db.get_damages_by_session(st.session_state['export_session'])
        detections = [
            {
                'lat': r.latitude, 'lon': r.longitude, 'type': r.damage_type,
                'timestamp': r.timestamp, 'conf': r.confidence, 'severity': r.severity
            }
            for r in records
        ]
        render_export_buttons(detections, db, st.session_state['export_session'])
        st.session_state['export_session'] = None
    
    # Back button
    if st.button("⬅️ Back to Inspection"):
        st.session_state['view_mode'] = 'inspection'
        st.rerun()
    
    st.stop()


# ==========================================
# 8. MAIN INSPECTION LAYOUT
# ==========================================
col_left, col_right = st.columns([1.8, 1])

with col_left:
    video_placeholder = render_video_container()
    progress_placeholder = st.empty()

with col_right:
    map_placeholder = render_live_map_container()
    stats_placeholder = st.empty()


# ==========================================
# 9. VIDEO PROCESSING
# ==========================================
if st.session_state['is_running'] and video_path is not None:
    
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
    
    # Load GPS file if provided
    if gps_config.get('file_path'):
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
    
    # Initialize Tracker
    tracker = SpatialDamageTracker(
        iou_threshold=st.session_state.get('tracker_iou', 0.3),
        max_age=30,
        min_hits=st.session_state.get('tracker_min_hits', 2),
        min_distance_meters=st.session_state.get('min_distance', 5.0)
    )
    
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
    
    frame_count = 0
    last_map_update = 0
    MAP_UPDATE_INTERVAL = 15  # Update map every N frames
    
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
            
            # ----- 1. DETECTION -----
            results = detector.model(frame, conf=conf_thresh, verbose=False)
            annotated_frame = results[0].plot()
            
            # ----- 2. GPS -----
            curr_lat, curr_lon = gps_manager.get_location_at_frame(frame_count, fps)
            
            # ----- 3. TRACKING -----
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
            
            # Update tracker - returns only NEW unique damages
            new_damages = tracker.update(frame_detections, (curr_lat, curr_lon))
            
            # ----- 4. SAVE NEW DAMAGES -----
            for dmg in new_damages:
                # Determine severity
                severity = "medium"
                if "pothole" in dmg['type'].lower() or "d40" in dmg['type'].lower():
                    severity = "high" if dmg['conf'] > 0.6 else "medium"
                elif "alligator" in dmg['type'].lower() or "d20" in dmg['type'].lower():
                    severity = "high" if dmg['conf'] > 0.7 else "medium"
                elif dmg['conf'] < 0.4:
                    severity = "low"
                
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
                    "frame_img": frame.copy()  # For live display
                }
                
                # Add to session state
                st.session_state['detections'].append(damage_data)
                
                # Save to database
                db.insert_damage(damage_data, session_id, frame.copy())
            
            # ----- 5. UPDATE UI -----
            
            # Video feed
            frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
            video_placeholder.image(frame_rgb, channels="RGB", use_container_width=True)
            
            # Progress bar (for file-based videos)
            if not is_stream and total_frames > 0:
                with progress_placeholder:
                    render_progress_bar(frame_count, total_frames, fps)
            
            # Map (update periodically, not every frame)
            if frame_count - last_map_update >= MAP_UPDATE_INTERVAL:
                update_live_map(map_placeholder, st.session_state['detections'])
                last_map_update = frame_count
            
            # Stats
            if new_damages or frame_count % 30 == 0:
                with stats_placeholder.container():
                    render_stats_panel(
                        st.session_state['detections'],
                        tracker.get_statistics()
                    )
            
            # Small delay to prevent UI freeze
            time.sleep(0.001)
    
    except Exception as e:
        st.error(f"Processing error: {e}")
    
    finally:
        cap.release()
        
        # End session
        db.end_session(session_id, gps_manager.get_total_distance_km())
        
        st.session_state['is_running'] = False
        
        # Show completion message
        st.success(f"✅ Inspection Complete! Found {len(st.session_state['detections'])} unique damages.")


# ==========================================
# 10. RESULTS SECTION (Always visible)
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
    - Use webcam or IP camera for live inspection
    - Upload GPX file from your GPS tracker for accurate location
    - Check the **HISTORY** button to view past inspections
    """)


# ==========================================
# 11. FOOTER
# ==========================================
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888; font-size: 0.8rem;">
    RoadGuard Vision v2.0 | AI-Powered Road Damage Detection System<br>
    Built with ❤️ using Streamlit, YOLOv8, and OpenCV
</div>
""", unsafe_allow_html=True)