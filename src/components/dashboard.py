import streamlit as st
from components.styling import render_icon_header

def render_stats_panel(detections):
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    render_icon_header("dashboard", "Real-time Metrics")
    
    col1, col2 = st.columns(2)
    
    # Hitung Statistik
    total_count = len(detections)
    last_type = detections[-1]['type'] if detections else "-"
    
    with col1:
        st.metric("Total Defects", total_count)
    with col2:
        st.metric("Last Detection", last_type)
        
    # Status Indikator
    if total_count > 0:
        st.markdown(f"""
        <div style="margin-top: 10px; padding: 8px; border-radius: 5px; background-color: rgba(255, 75, 75, 0.2); border: 1px solid #FF4B4B; color: #ff9999; text-align: center; font-size: 0.8rem;">
            ⚠️ Alert: {last_type} Detected!
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="margin-top: 10px; padding: 8px; border-radius: 5px; background-color: rgba(0, 255, 0, 0.1); border: 1px solid #00FF00; color: #99ff99; text-align: center; font-size: 0.8rem;">
            ✅ System Scanning...
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown('</div>', unsafe_allow_html=True)

def render_video_container():
    """Mengembalikan placeholder kosong yang sudah dibungkus style"""
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    render_icon_header("video", "Live Feed")
    placeholder = st.empty()
    st.markdown('</div>', unsafe_allow_html=True)
    return placeholder