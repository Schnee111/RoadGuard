import streamlit as st
import pandas as pd
import folium
import base64
import cv2
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
from components.styling import render_icon_header

# HELPER: Konversi Gambar OpenCV ke Base64 String
def encode_image_to_base64(cv2_img):
    _, buffer = cv2.imencode('.jpg', cv2_img)
    jpg_as_text = base64.b64encode(buffer).decode('utf-8')
    return jpg_as_text

def render_live_map_container():
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    render_icon_header("map", "Tracking")
    map_placeholder = st.empty()
    st.markdown('</div>', unsafe_allow_html=True)
    return map_placeholder

def update_live_map(placeholder, detections):
    if detections:
        # Untuk live map (st.map), kita tidak butuh gambar, hanya titik
        df = pd.DataFrame(detections)
        placeholder.map(df, latitude='lat', longitude='lon', size=20, zoom=15, width='stretch')

def render_analysis_map(detections):
    if not detections:
        st.info("No data available for analysis.")
        return

    df = pd.DataFrame(detections)
    
    # 1. Setup Peta
    center_lat = df['lat'].mean()
    center_lon = df['lon'].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=15, tiles="CartoDB dark_matter")
    marker_cluster = MarkerCluster().add_to(m)
    
    # 2. Loop Data & Buat Popup Gambar
    for idx, row in df.iterrows():
        # Encode gambar (jika ada di memory)
        img_html = ""
        if 'frame_img' in row:
            # Resize dulu agar popup tidak lemot/besar
            small_img = cv2.resize(row['frame_img'], (200, 150)) 
            b64_str = encode_image_to_base64(small_img)
            img_html = f'<img src="data:image/jpeg;base64,{b64_str}" width="200" style="border-radius:5px; margin-top:5px;">'
        
        # Warna Marker
        color = "red" if "Pothole" in row['type'] or "Lubang" in row['type'] else "orange"
        
        # HTML Popup Content
        popup_html = f"""
        <div style="font-family: sans-serif; min-width: 210px;">
            <h5 style="margin:0; color: #333;">{row['type']}</h5>
            <hr style="margin: 5px 0;">
            <p style="font-size: 11px; margin:0; color: #666;">Time: {row['timestamp']:.2f}s</p>
            {img_html}
        </div>
        """
        
        folium.Marker(
            location=[row['lat'], row['lon']],
            popup=folium.Popup(popup_html, max_width=250),
            icon=folium.Icon(color=color, icon="camera", prefix="fa")
        ).add_to(marker_cluster)
    
    st.subheader("📋 Comprehensive Report")
    st_folium(m, width="100%", height=500)
    
    # Tampilkan tabel tanpa kolom gambar raw (agar tidak error)
    st.dataframe(df.drop(columns=['frame_img'], errors='ignore'), width='stretch')