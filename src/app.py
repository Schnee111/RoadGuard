import streamlit as st
import cv2
import pandas as pd
import time
from modules.detector import RoadDamageDetector
from modules.gps_manager import GPSManager

# Import Komponen
from components.styling import load_css
from components.sidebar import render_sidebar
from components.dashboard import render_stats_panel, render_video_container
from components.map_view import render_live_map_container, update_live_map, render_analysis_map

# 1. SETUP UI
st.set_page_config(page_title="RoadGuard Vision", layout="wide", page_icon="🛡️")
load_css()

# 2. STATE MANAGEMENT
if 'detections' not in st.session_state:
    st.session_state['detections'] = []
if 'is_running' not in st.session_state:
    st.session_state['is_running'] = False

# 3. RENDER LAYOUT
st.markdown('<div class="header-title">RoadGuard Vision</div>', unsafe_allow_html=True)
st.markdown('<div class="header-subtitle">AI-Powered Road Inspection System</div>', unsafe_allow_html=True)

# Panggil Sidebar (Sekarang menerima stop_btn)
start_btn, stop_btn, reset_btn, video_path, conf_thresh = render_sidebar()

# Logika Tombol
if start_btn:
    st.session_state['is_running'] = True
if stop_btn:
    st.session_state['is_running'] = False
if reset_btn:
    st.session_state['detections'] = []
    st.session_state['is_running'] = False
    st.rerun()

# Layout Grid
col_left, col_right = st.columns([1.8, 1])

with col_left:
    video_placeholder = render_video_container()

with col_right:
    map_placeholder = render_live_map_container()
    stats_placeholder = st.empty()

# 4. LOGIKA PROCESSING (Jalan hanya jika is_running == True)
if st.session_state['is_running']:
    # Init Logic
    detector = RoadDamageDetector(model_path='src/models/YOLOv8_small_RDD.pt') 
    gps_manager = GPSManager() 
    
    cap = cv2.VideoCapture(video_path)
    frame_count = 0
    last_saved_lat, last_saved_lon = 0, 0

if start_btn:
    # Init Modules
    detector = RoadDamageDetector(model_path='src/models/YOLOv8_small_RDD.pt') 
    gps_manager = GPSManager() 
    
    cap = cv2.VideoCapture(video_path)
    frame_count = 0
    
    # VARIABEL BARU UNTUK COOLDOWN
    # Format: {"Pothole": frame_terakhir_disimpan, "Alligator Crack": frame_terakhir_disimpan}
    cooldown_tracker = {} 
    COOLDOWN_FRAMES = 90  # 90 frame = kira-kira 3 detik (asumsi 30fps)
    
    # VARIABEL UNTUK HITUNG FPS
    prev_time = 0
    curr_time = 0
    fps_list = [] # Untuk menyimpan semua nilai FPS agar bisa dirata-rata nanti
    
    col1, col2 = st.columns([3, 1]) # Buat kolom biar FPS tampil di sebelah video
    
    with col1:
        video_placeholder = render_video_container()
    with col2:
        fps_placeholder = st.empty() # Placeholder untuk angka FPS
        stats_placeholder = st.empty()

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break
        
        # --- LOGIKA HITUNG FPS (Mulai) ---
        curr_time = time.time()
        fps = 1 / (curr_time - prev_time) if prev_time != 0 else 0
        prev_time = curr_time
        fps_list.append(fps) # Simpan ke list
        # --- LOGIKA HITUNG FPS (Selesai) ---

        frame_count += 1
        
        # 1. VISUAL: Selalu deteksi & gambar kotak (Visual Real-time)
        results = detector.model(frame, conf=conf_thresh, verbose=False)
        annotated_frame = results[0].plot()
        
        # 2. GPS
        curr_lat, curr_lon = gps_manager.get_location_at_frame(frame_count)
        
        # 3. LOGIC: Filter Data untuk Laporan
        has_new_valid_data = False
        
        if results[0].boxes:
            # Ambil 1 deteksi terbaik saja per frame
            best_box = results[0].boxes[0]
            label = detector.model.names[int(best_box.cls[0])]
            
            # CEK COOLDOWN
            last_saved_frame = cooldown_tracker.get(label, -9999)
            
            # Hanya simpan jika sudah melewati masa cooldown (3 detik dari deteksi terakhir tipe ini)
            if (frame_count - last_saved_frame) > COOLDOWN_FRAMES:
                
                # Simpan Data
                st.session_state['detections'].append({
                    "timestamp": frame_count / 30,
                    "lat": curr_lat,
                    "lon": curr_lon,
                    "type": label,
                    "frame_img": frame # Simpan raw image untuk diproses nanti
                })
                
                # Update Tracker
                cooldown_tracker[label] = frame_count
                has_new_valid_data = True

        # 4. UPDATE UI
        frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
        video_placeholder.image(frame_rgb, channels="RGB", width='stretch')

        # Tampilkan FPS secara Real-time
        fps_placeholder.metric("Processing Speed", f"{int(fps)} FPS")
        
        if has_new_valid_data:
            update_live_map(map_placeholder, st.session_state['detections'])
            with stats_placeholder.container():
                render_stats_panel(st.session_state['detections'])

    cap.release()
    st.success("Inspection Complete.")
    # HITUNG RATA-RATA AKHIR
    avg_fps = sum(fps_list) / len(fps_list) if fps_list else 0
    st.success(f"Inspection Complete. Average FPS: {avg_fps:.2f}")

# Render Laporan Akhir
st.markdown("---")
render_analysis_map(st.session_state['detections'])