"""
Dashboard Component for RoadGuard
Menampilkan statistik dan metrik real-time.
"""

import streamlit as st
import pandas as pd
from components.styling import render_icon_header


def render_stats_panel(detections: list, tracker_stats: dict = None):
    """
    Render panel statistik real-time.
    
    Args:
        detections: List of detection dicts
        tracker_stats: Optional stats from DamageTracker
    """
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    render_icon_header("dashboard", "Real-time Metrics")
    
    # Hitung statistik
    total_count = len(detections)
    
    if detections:
        df = pd.DataFrame(detections)
        last_type = detections[-1].get('type', '-')
        
        # Count by severity
        if 'severity' in df.columns:
            high_count = len(df[df['severity'] == 'high'])
            medium_count = len(df[df['severity'] == 'medium'])
            low_count = len(df[df['severity'] == 'low'])
        else:
            high_count = medium_count = low_count = 0
        
        # Count by type
        type_col = 'type' if 'type' in df.columns else 'damage_type'
        if type_col in df.columns:
            type_counts = df[type_col].value_counts().to_dict()
        else:
            type_counts = {}
    else:
        last_type = "-"
        high_count = medium_count = low_count = 0
        type_counts = {}
    
    # Main metrics row
    col1, col2 = st.columns(2)
    with col1:
        st.metric("🔍 Total Defects", total_count)
    with col2:
        st.metric("📍 Last Detection", last_type[:15] if len(last_type) > 15 else last_type)
    
    # Severity breakdown
    if total_count > 0:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🔴 High", high_count)
        with col2:
            st.metric("🟠 Medium", medium_count)
        with col3:
            st.metric("🟢 Low", low_count)
    
    # Tracker stats (if available)
    if tracker_stats:
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            st.caption(f"Active Tracks: {tracker_stats.get('active_tracks', 0)}")
        with col2:
            st.caption(f"Frames: {tracker_stats.get('frames_processed', 0)}")
    
    # Alert indicator
    if total_count > 0:
        # Determine alert color based on severity
        if high_count > 0:
            alert_color = "rgba(255, 75, 75, 0.2)"
            border_color = "#FF4B4B"
            text_color = "#ff9999"
            alert_msg = f"⚠️ {high_count} High Severity Damage(s) Detected!"
        else:
            alert_color = "rgba(255, 165, 0, 0.2)"
            border_color = "#FFA500"
            text_color = "#ffcc80"
            alert_msg = f"⚡ {last_type} Detected"
        
        st.markdown(f"""
        <div style="margin-top: 10px; padding: 8px; border-radius: 5px; 
                    background-color: {alert_color}; border: 1px solid {border_color}; 
                    color: {text_color}; text-align: center; font-size: 0.8rem;">
            {alert_msg}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="margin-top: 10px; padding: 8px; border-radius: 5px; 
                    background-color: rgba(0, 255, 0, 0.1); border: 1px solid #00FF00; 
                    color: #99ff99; text-align: center; font-size: 0.8rem;">
            ✅ System Scanning...
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)


def render_video_container():
    """Render container untuk video feed dengan styling"""
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    render_icon_header("video", "Live Feed")
    placeholder = st.empty()
    st.markdown('</div>', unsafe_allow_html=True)
    return placeholder


def render_progress_bar(current_frame: int, total_frames: int, fps: float = 30.0):
    """
    Render progress bar untuk video processing.
    
    Args:
        current_frame: Frame saat ini
        total_frames: Total frame dalam video
        fps: Frames per second
    """
    if total_frames <= 0:
        return
    
    progress = min(1.0, current_frame / total_frames)
    current_time = current_frame / fps
    total_time = total_frames / fps
    
    st.progress(progress, text=f"Processing: {current_time:.1f}s / {total_time:.1f}s ({progress*100:.1f}%)")


def render_session_summary(detections: list, gps_manager=None, db=None, session_id: str = None):
    """
    Render ringkasan setelah sesi selesai.
    
    Args:
        detections: List of detection dicts
        gps_manager: GPSManager instance untuk jarak
        db: DamageDatabase instance
        session_id: Session ID
    """
    st.markdown("## 📊 Inspection Summary")
    
    total = len(detections)
    
    if total == 0:
        st.info("No damages detected in this session.")
        return
    
    df = pd.DataFrame(detections)
    
    # Overview cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 20px; border-radius: 10px; text-align: center;">
            <h2 style="margin: 0; color: white;">{}</h2>
            <p style="margin: 5px 0 0 0; color: rgba(255,255,255,0.8); font-size: 0.9rem;">Total Damages</p>
        </div>
        """.format(total), unsafe_allow_html=True)
    
    with col2:
        if 'severity' in df.columns:
            high = len(df[df['severity'] == 'high'])
        else:
            high = 0
        st.markdown("""
        <div style="background: linear-gradient(135deg, #f5576c 0%, #f093fb 100%);
                    padding: 20px; border-radius: 10px; text-align: center;">
            <h2 style="margin: 0; color: white;">{}</h2>
            <p style="margin: 5px 0 0 0; color: rgba(255,255,255,0.8); font-size: 0.9rem;">High Severity</p>
        </div>
        """.format(high), unsafe_allow_html=True)
    
    with col3:
        if gps_manager:
            distance = gps_manager.get_total_distance_km()
        else:
            distance = 0
        st.markdown("""
        <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                    padding: 20px; border-radius: 10px; text-align: center;">
            <h2 style="margin: 0; color: white;">{:.2f}</h2>
            <p style="margin: 5px 0 0 0; color: rgba(255,255,255,0.8); font-size: 0.9rem;">Distance (km)</p>
        </div>
        """.format(distance), unsafe_allow_html=True)
    
    with col4:
        if total > 0 and distance > 0:
            rate = total / distance
        else:
            rate = 0
        st.markdown("""
        <div style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
                    padding: 20px; border-radius: 10px; text-align: center;">
            <h2 style="margin: 0; color: white;">{:.1f}</h2>
            <p style="margin: 5px 0 0 0; color: rgba(255,255,255,0.8); font-size: 0.9rem;">Damage/km</p>
        </div>
        """.format(rate), unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Damage type distribution
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Damage Types")
        type_col = 'type' if 'type' in df.columns else 'damage_type'
        if type_col in df.columns:
            type_counts = df[type_col].value_counts()
            for dtype, count in type_counts.items():
                pct = count / total * 100
                st.progress(pct / 100, text=f"{dtype}: {count} ({pct:.1f}%)")
    
    with col2:
        st.markdown("### Severity Distribution")
        if 'severity' in df.columns:
            sev_counts = df['severity'].value_counts()
            colors = {'high': '🔴', 'medium': '🟠', 'low': '🟢'}
            for sev, count in sev_counts.items():
                pct = count / total * 100
                icon = colors.get(sev, '⚪')
                st.progress(pct / 100, text=f"{icon} {sev.title()}: {count} ({pct:.1f}%)")


def render_compact_stats(detections: list):
    """
    Render compact stats untuk sidebar atau small space.
    
    Args:
        detections: List of detection dicts
    """
    total = len(detections)
    
    if total == 0:
        st.caption("No detections yet")
        return
    
    df = pd.DataFrame(detections)
    
    # Count by severity
    if 'severity' in df.columns:
        high = len(df[df['severity'] == 'high'])
        medium = len(df[df['severity'] == 'medium'])
        low = len(df[df['severity'] == 'low'])
    else:
        high = medium = low = 0
    
    st.markdown(f"""
    <div style="display: flex; justify-content: space-between; font-size: 0.8rem;">
        <span>🔍 {total}</span>
        <span>🔴 {high}</span>
        <span>🟠 {medium}</span>
        <span>🟢 {low}</span>
    </div>
    """, unsafe_allow_html=True)