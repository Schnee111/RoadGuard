import streamlit as st
import tempfile
from components.styling import render_icon_header

def render_sidebar():
    with st.sidebar:
        render_icon_header("settings", "System Control")
        st.markdown("---")
        
        # 1. Pilihan Sumber Video
        source_type = st.radio("Input Source", ["Demo Video", "Upload File"], label_visibility="collapsed")
        
        video_path = "sample_videos/jalan_rusak_demo.mp4" # Default
        
        if source_type == "Upload File":
            uploaded_file = st.file_uploader("Select MP4", type=['mp4'], label_visibility="collapsed")
            if uploaded_file:
                tfile = tempfile.NamedTemporaryFile(delete=False)
                tfile.write(uploaded_file.read())
                video_path = tfile.name
        
        st.markdown("### Parameters")
        conf_thresh = st.slider("AI Sensitivity", 0.1, 1.0, 0.35)
        
        st.markdown("---")
        
        # 3. Tombol Aksi (Layout Baru: Start & Stop Jejer)
        col1, col2 = st.columns(2)
        start_btn = col1.button("START", type="primary", width='stretch')
        stop_btn = col2.button("STOP", type="secondary", width='stretch')
        
        # Tombol Reset di bawah
        reset_btn = st.button("RESET SYSTEM", width='stretch')
        
        return start_btn, stop_btn, reset_btn, video_path, conf_thresh