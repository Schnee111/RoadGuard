"""
Sidebar Component for RoadGuard
Menangani semua kontrol input dan parameter sistem.
"""

import streamlit as st
import tempfile
import os
from components.styling import render_icon_header


def render_sidebar():
    """
    Render sidebar dengan kontrol lengkap:
    - Multi-source input (Demo, Upload, Webcam, IP Camera)
    - GPS input options (Simulasi, Manual, Upload GPX/CSV, REALTIME)
    - AI Parameters
    - Action buttons
    
    Returns:
        Tuple: (start_btn, stop_btn, reset_btn, video_path, conf_thresh, gps_config, view_history_btn)
    """
    with st.sidebar:
        render_icon_header("settings", "System Control")
        st.markdown("---")
        
        # ==========================================
        # 1. VIDEO SOURCE SELECTION
        # ==========================================
        st.markdown("### 📹 Video Source")
        
        source_type = st.radio(
            "Input Source", 
            ["Demo Video", "Upload File", "📷 Webcam", "📡 IP Camera/RTSP"],
            label_visibility="collapsed",
            help="Pilih sumber video untuk inspeksi"
        )
        
        video_path = "video/jalan_rusak_demo.mp4"  # Default
        
        if source_type == "Demo Video":
            # Cek apakah demo video tersedia
            demo_videos = []
            video_dirs = ["video", "sample_videos", "videos", "../video"]
            for vdir in video_dirs:
                if os.path.exists(vdir):
                    for f in os.listdir(vdir):
                        if f.endswith(('.mp4', '.avi', '.mov')):
                            demo_videos.append(os.path.join(vdir, f))
            
            if demo_videos:
                video_path = st.selectbox(
                    "Select Demo Video",
                    demo_videos,
                    label_visibility="collapsed"
                )
            else:
                st.warning("⚠️ No demo videos found. Add videos to the video/ folder")
                video_path = None
                
        elif source_type == "Upload File":
            uploaded_file = st.file_uploader(
                "Select Video File", 
                type=['mp4', 'avi', 'mov', 'mkv'],
                label_visibility="collapsed",
                help="Upload video MP4/AVI untuk dianalisis"
            )
            if uploaded_file:
                # Simpan ke temp file
                tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
                tfile.write(uploaded_file.read())
                video_path = tfile.name
            else:
                video_path = None
                
        elif source_type == "📷 Webcam":
            # Pilihan kamera
            camera_idx = st.number_input(
                "Camera Index", 
                min_value=0, 
                max_value=5, 
                value=0,
                help="0 = webcam default, 1-5 = kamera eksternal"
            )
            video_path = int(camera_idx)
            st.info("💡 Webcam akan aktif saat START ditekan")
            
            # Saran untuk HP
            with st.expander("📱 Gunakan Kamera HP"):
                st.markdown("""
                **Untuk menggunakan kamera HP sebagai webcam:**
                
                1. **Android - DroidCam:**
                   - Install DroidCam di HP (Play Store)
                   - Install DroidCam Client di laptop
                   - Hubungkan via WiFi atau USB
                   - Pilih Camera Index yang sesuai
                
                2. **Android - IP Webcam:**
                   - Install IP Webcam (Play Store)
                   - Start server di HP
                   - Gunakan mode "IP Camera/RTSP"
                   - Masukkan URL: `http://IP_HP:8080/video`
                
                3. **iPhone - EpocCam:**
                   - Install EpocCam di iPhone
                   - Install driver di laptop
                   - Hubungkan via WiFi
                """)
            
        elif source_type == "📡 IP Camera/RTSP":
            rtsp_url = st.text_input(
                "RTSP/HTTP URL",
                placeholder="rtsp://192.168.1.1:554/stream",
                help="Masukkan URL stream dari IP camera"
            )
            
            # Contoh URL
            with st.expander("📋 Contoh URL"):
                st.code("""
# IP Camera RTSP
rtsp://admin:password@192.168.1.100:554/stream1

# HTTP Stream
http://192.168.1.100:8080/video

# Android IP Webcam App
http://192.168.1.100:8080/video

# DroidCam
http://192.168.1.100:4747/video
                """)
            
            video_path = rtsp_url if rtsp_url else None
        
        st.markdown("---")
        
        # ==========================================
        # 2. GPS/LOCATION SETTINGS
        # ==========================================
        st.markdown("### 📍 Location Data")
        
        gps_mode = st.radio(
            "GPS Mode",
            ["🔴 Realtime (Browser)", "Simulasi", "Manual Input", "Upload GPX/CSV"],
            label_visibility="collapsed",
            help="Pilih sumber data lokasi GPS"
        )
        
        gps_config = {
            "mode": "simulation",
            "start_lat": -6.9024,
            "start_lon": 107.6188,
            "end_lat": -6.9024,
            "end_lon": 107.6188,
            "file_path": None
        }
        
        if gps_mode == "🔴 Realtime (Browser)":
            gps_config["mode"] = "realtime"
            
            st.success("📍 GPS Realtime Aktif")
            st.caption("Lokasi akan diambil dari browser HP/Laptop Anda")
            
            with st.expander("ℹ️ Cara Kerja GPS Realtime"):
                st.markdown("""
                **Untuk HP:**
                1. Buka aplikasi ini di browser HP (Chrome/Safari)
                2. Izinkan akses lokasi saat diminta
                3. Pastikan GPS HP aktif
                4. Lokasi akan update otomatis saat bergerak
                
                **Untuk Laptop:**
                1. Browser akan menggunakan WiFi/IP location
                2. Akurasi mungkin lebih rendah dari HP
                3. Untuk akurasi lebih baik, gunakan HP
                
                **Tips:**
                - Gunakan HTTPS untuk akses lokasi (localhost ok)
                - Pastikan browser memiliki permission lokasi
                - Di outdoor, akurasi GPS HP bisa < 5 meter
                """)
            
            # Show current GPS status placeholder
            if 'realtime_gps' in st.session_state and st.session_state['realtime_gps']:
                gps_data = st.session_state['realtime_gps']
                st.metric("Current Position", 
                         f"{gps_data.get('lat', 0):.6f}, {gps_data.get('lon', 0):.6f}")
                st.caption(f"Accuracy: {gps_data.get('accuracy', 0):.1f}m")
        
        elif gps_mode == "Simulasi":
            gps_config["mode"] = "simulation"
            
            with st.expander("⚙️ Simulation Settings"):
                col1, col2 = st.columns(2)
                gps_config["start_lat"] = col1.number_input(
                    "Start Lat", 
                    value=-6.9024, 
                    format="%.6f",
                    help="Latitude titik awal"
                )
                gps_config["start_lon"] = col2.number_input(
                    "Start Lon", 
                    value=107.6188, 
                    format="%.6f",
                    help="Longitude titik awal"
                )
                
        elif gps_mode == "Manual Input":
            gps_config["mode"] = "manual"
            
            st.markdown("**Titik Awal:**")
            col1, col2 = st.columns(2)
            gps_config["start_lat"] = col1.number_input(
                "Lat Awal", 
                value=-6.9024, 
                format="%.6f",
                label_visibility="collapsed"
            )
            gps_config["start_lon"] = col2.number_input(
                "Lon Awal", 
                value=107.6188, 
                format="%.6f",
                label_visibility="collapsed"
            )
            
            st.markdown("**Titik Akhir:**")
            col1, col2 = st.columns(2)
            gps_config["end_lat"] = col1.number_input(
                "Lat Akhir", 
                value=-6.9124, 
                format="%.6f",
                label_visibility="collapsed"
            )
            gps_config["end_lon"] = col2.number_input(
                "Lon Akhir", 
                value=107.6288, 
                format="%.6f",
                label_visibility="collapsed"
            )
            
            st.caption("📌 Lokasi akan diinterpolasi linear dari titik awal ke akhir")
            
        elif gps_mode == "Upload GPX/CSV":
            gps_file = st.file_uploader(
                "Upload GPS Track",
                type=['gpx', 'csv'],
                label_visibility="collapsed",
                help="Upload file GPX dari GPS tracker atau CSV dengan kolom lat, lon"
            )
            
            if gps_file:
                # Simpan ke temp
                suffix = '.gpx' if gps_file.name.endswith('.gpx') else '.csv'
                tfile = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                tfile.write(gps_file.read())
                gps_config["file_path"] = tfile.name
                gps_config["mode"] = "gpx" if suffix == '.gpx' else "csv"
                st.success(f"✅ Loaded: {gps_file.name}")
            else:
                gps_config["mode"] = "simulation"
            
            with st.expander("📋 Format yang Didukung"):
                st.markdown("""
                **CSV Format:**
                ```
                timestamp,latitude,longitude
                0,−6.9024,107.6188
                1,−6.9025,107.6189
                ...
                ```
                
                **GPX Format:** Standard dari Strava, Garmin, dll.
                """)
        
        st.markdown("---")
        
        # ==========================================
        # 3. AI PARAMETERS
        # ==========================================
        st.markdown("### 🤖 AI Parameters")
        
        conf_thresh = st.slider(
            "Detection Confidence",
            min_value=0.1,
            max_value=1.0,
            value=0.35,
            step=0.05,
            help="Semakin tinggi = semakin yakin (tapi bisa miss deteksi)"
        )
        
        with st.expander("⚙️ Advanced Settings"):
            st.session_state['tracker_iou'] = st.slider(
                "Tracker IoU Threshold",
                min_value=0.1,
                max_value=0.8,
                value=0.3,
                step=0.05,
                help="Threshold untuk menganggap 2 deteksi adalah objek yang sama"
            )
            
            st.session_state['tracker_min_hits'] = st.slider(
                "Min Detection Hits",
                min_value=1,
                max_value=5,
                value=2,
                help="Minimal berapa frame terdeteksi sebelum dianggap valid"
            )
            
            st.session_state['min_distance'] = st.slider(
                "Min GPS Distance (m)",
                min_value=1.0,
                max_value=20.0,
                value=5.0,
                step=1.0,
                help="Jarak minimal antar kerusakan yang sama (spatial dedup)"
            )
        
        st.markdown("---")
        
        # ==========================================
        # 4. ACTION BUTTONS
        # ==========================================
        col1, col2 = st.columns(2)
        start_btn = col1.button("▶️ START", type="primary", use_container_width=True)
        stop_btn = col2.button("⏹️ STOP", type="secondary", use_container_width=True)
        
        col3, col4 = st.columns(2)
        reset_btn = col3.button("🔄 RESET", use_container_width=True)
        view_history_btn = col4.button("📊 HISTORY", use_container_width=True)
        
        # ==========================================
        # 5. SESSION INFO
        # ==========================================
        st.markdown("---")
        
        if 'session_id' in st.session_state and st.session_state.get('is_running'):
            st.markdown("### 📋 Current Session")
            st.caption(f"ID: `{st.session_state['session_id'][:20]}...`")
            
            if 'detections' in st.session_state:
                st.metric("Damages Found", len(st.session_state['detections']))
        
        return start_btn, stop_btn, reset_btn, video_path, conf_thresh, gps_config, view_history_btn


def render_history_view(db):
    """
    Render tampilan history/riwayat inspeksi.
    
    Args:
        db: DamageDatabase instance
    """
    st.markdown("## 📊 Inspection History")
    
    sessions = db.get_all_sessions()
    
    if not sessions:
        st.info("Belum ada data inspeksi tersimpan.")
        return
    
    # Statistik ringkas
    stats = db.get_statistics()
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Sessions", stats.get('total_sessions', 0))
    col2.metric("Total Damages", stats.get('total_damages', 0))
    
    if stats.get('by_severity'):
        high_sev = stats['by_severity'].get('high', 0)
        col3.metric("High Severity", high_sev)
    
    st.markdown("---")
    
    # List sessions
    for session in sessions[:10]:  # Limit 10 terbaru
        session_dict = dict(session) if hasattr(session, 'keys') else {
            'id': session[0],
            'start_time': session[1],
            'end_time': session[2],
            'video_source': session[3],
            'total_damages': session[4],
            'total_distance_km': session[5],
            'status': session[6]
        }
        
        with st.expander(f"📁 {session_dict['id'][:20]}... - {session_dict.get('status', 'unknown')}"):
            col1, col2 = st.columns(2)
            col1.write(f"**Start:** {session_dict.get('start_time', 'N/A')}")
            col2.write(f"**End:** {session_dict.get('end_time') or 'In Progress'}")
            
            col1, col2 = st.columns(2)
            col1.write(f"**Damages:** {session_dict.get('total_damages', 0)}")
            dist = session_dict.get('total_distance_km', 0) or 0
            col2.write(f"**Distance:** {dist:.2f} km")
            
            if session_dict.get('video_source'):
                st.write(f"**Source:** {session_dict['video_source']}")
            
            # Tombol aksi
            col1, col2, col3 = st.columns(3)
            if col1.button("📍 View Map", key=f"map_{session_dict['id']}"):
                st.session_state['view_session'] = session_dict['id']
            if col2.button("📥 Export", key=f"export_{session_dict['id']}"):
                st.session_state['export_session'] = session_dict['id']
            if col3.button("🗑️ Delete", key=f"del_{session_dict['id']}"):
                db.delete_session(session_dict['id'])
                st.rerun()
