"""
Map View Component for RoadGuard
Menampilkan peta interaktif dengan berbagai fitur visualisasi.
"""

import streamlit as st
import pandas as pd
import folium
import base64
import cv2
import os
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster, HeatMap, MiniMap, Fullscreen
from components.styling import render_icon_header


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def encode_image_to_base64(cv2_img) -> str:
    """Konversi gambar OpenCV ke Base64 string untuk display di popup"""
    if cv2_img is None:
        return ""
    try:
        _, buffer = cv2.imencode('.jpg', cv2_img)
        jpg_as_text = base64.b64encode(buffer).decode('utf-8')
        return jpg_as_text
    except Exception:
        return ""


def load_image_from_path(image_path: str) -> str:
    """Load gambar dari file path dan konversi ke base64"""
    if not image_path:
        print(f"⚠️ No image path provided")
        return ""
    
    # Normalize path untuk cross-platform
    image_path = os.path.normpath(image_path)
    
    if not os.path.exists(image_path):
        print(f"⚠️ Image file not found: {image_path}")
        # Try with absolute path
        abs_path = os.path.abspath(image_path)
        if os.path.exists(abs_path):
            image_path = abs_path
            print(f"✅ Found using absolute path: {abs_path}")
        else:
            return ""
    
    try:
        with open(image_path, 'rb') as f:
            img_data = f.read()
            b64 = base64.b64encode(img_data).decode('utf-8')
            print(f"✅ Loaded image from: {image_path} (size: {len(img_data)} bytes)")
            return b64
    except Exception as e:
        print(f"❌ Error loading image {image_path}: {e}")
        return ""


def get_damage_color(damage_type: str, severity: str = "medium") -> str:
    """Tentukan warna marker berdasarkan tipe kerusakan dan severity"""
    # Berdasarkan severity
    severity_colors = {
        "high": "red",
        "medium": "orange", 
        "low": "blue"
    }
    
    # Berdasarkan tipe (override jika tipe tertentu)
    type_lower = damage_type.lower()
    
    if "pothole" in type_lower or "lubang" in type_lower or "d40" in type_lower:
        return "red"
    elif "alligator" in type_lower or "buaya" in type_lower or "d20" in type_lower:
        return "darkred"
    elif "longitudinal" in type_lower or "memanjang" in type_lower or "d00" in type_lower:
        return "orange"
    elif "transverse" in type_lower or "melintang" in type_lower or "d10" in type_lower:
        return "cadetblue"
    else:
        return severity_colors.get(severity, "gray")


def get_damage_icon(damage_type: str) -> str:
    """Tentukan icon marker berdasarkan tipe kerusakan"""
    type_lower = damage_type.lower()
    
    if "pothole" in type_lower or "lubang" in type_lower:
        return "circle"
    elif "crack" in type_lower or "retak" in type_lower:
        return "bolt"
    elif "marka" in type_lower:
        return "road"
    else:
        return "camera"


# ==========================================
# LIVE MAP (Real-time tracking)
# ==========================================

def render_live_map_container():
    """Render container untuk live map"""
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    render_icon_header("map", "Live Tracking")
    map_placeholder = st.empty()
    st.markdown('</div>', unsafe_allow_html=True)
    return map_placeholder


def update_live_map(placeholder, detections: list):
    """
    Update live map dengan deteksi terbaru.
    Menggunakan st.map untuk performa real-time.
    """
    if detections:
        df = pd.DataFrame(detections)
        if 'lat' in df.columns and 'lon' in df.columns:
            placeholder.map(
                df, 
                latitude='lat', 
                longitude='lon', 
                size=20, 
                zoom=15,
                width='stretch'
            )


# ==========================================
# ANALYSIS MAP (Full featured)
# ==========================================

def render_analysis_map(detections: list, db=None, show_filters: bool = True):
    """
    Render peta analisis lengkap dengan fitur:
    - Filter by damage type
    - Filter by severity
    - Heatmap mode
    - Cluster markers
    - Image popups
    - Export options
    
    Args:
        detections: List of detection dicts (dari session_state atau database)
        db: Optional DamageDatabase instance untuk load image dari file
        show_filters: Tampilkan panel filter atau tidak
    """
    if not detections:
        st.info("📍 No damage data available for mapping. Start an inspection first!")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(detections)
    
    # Pastikan kolom yang dibutuhkan ada
    required_cols = ['lat', 'lon', 'type']
    for col in required_cols:
        if col not in df.columns:
            st.error(f"Missing required column: {col}")
            return
    
    # Default values untuk kolom opsional
    if 'severity' not in df.columns:
        df['severity'] = 'medium'
    if 'timestamp' not in df.columns:
        df['timestamp'] = 0
    if 'conf' not in df.columns:
        df['conf'] = 0.5
    
    st.markdown("---")
    st.subheader("📋 Damage Analysis Report")
    
    # ==========================================
    # FILTER PANEL
    # ==========================================
    if show_filters:
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            # Filter by damage type
            damage_types = df['type'].unique().tolist()
            selected_types = st.multiselect(
                "🔍 Filter by Damage Type",
                damage_types,
                default=damage_types,
                help="Pilih tipe kerusakan yang ingin ditampilkan"
            )
        
        with col2:
            # Filter by severity
            severities = df['severity'].unique().tolist()
            selected_severities = st.multiselect(
                "⚠️ Filter by Severity",
                severities,
                default=severities,
                help="Pilih tingkat keparahan"
            )
        
        with col3:
            # View mode
            view_mode = st.radio(
                "View Mode",
                ["Markers", "Heatmap", "Both"],
                horizontal=False,
                label_visibility="collapsed"
            )
        
        # Apply filters
        df_filtered = df[
            (df['type'].isin(selected_types)) & 
            (df['severity'].isin(selected_severities))
        ]
    else:
        df_filtered = df
        view_mode = "Markers"
    
    if df_filtered.empty:
        st.warning("No data matches the current filters.")
        return
    
    # ==========================================
    # CREATE MAP
    # ==========================================
    center_lat = df_filtered['lat'].mean()
    center_lon = df_filtered['lon'].mean()
    
    # Pilih tile layer
    m = folium.Map(
        location=[center_lat, center_lon], 
        zoom_start=15,
        tiles="CartoDB dark_matter"
    )
    
    # Tambah layer alternatif
    folium.TileLayer('CartoDB positron', name='Light Mode').add_to(m)
    folium.TileLayer('OpenStreetMap', name='Street Map').add_to(m)
    
    # Add plugins
    Fullscreen(position='topleft').add_to(m)
    MiniMap(toggle_display=True).add_to(m)
    
    # ==========================================
    # HEATMAP LAYER
    # ==========================================
    if view_mode in ["Heatmap", "Both"]:
        heat_data = df_filtered[['lat', 'lon']].values.tolist()
        
        # Weight by severity
        weights = df_filtered['severity'].map({
            'high': 1.0,
            'medium': 0.6,
            'low': 0.3
        }).fillna(0.5).tolist()
        
        heat_data_weighted = [[row[0], row[1], w] for row, w in zip(heat_data, weights)]
        
        HeatMap(
            heat_data_weighted,
            min_opacity=0.3,
            max_zoom=18,
            radius=25,
            blur=15,
            gradient={0.4: 'blue', 0.65: 'lime', 0.8: 'orange', 1: 'red'}
        ).add_to(m)
    
    # ==========================================
    # MARKER LAYER
    # ==========================================
    if view_mode in ["Markers", "Both"]:
        marker_cluster = MarkerCluster(name="Damage Points").add_to(m)
        
        for idx, row in df_filtered.iterrows():
            # Prepare image HTML
            img_html = ""
            
            # Debug: print row data
            print("\n=== Processing marker", idx, "===")
            print("Type:", row.get('type'))
            print("Has frame_img:", 'frame_img' in row and row['frame_img'] is not None)
            print("Has image_path:", 'image_path' in row and row.get('image_path'))
            if 'image_path' in row:
                print("Image path value:", row['image_path'])
            
            # Cek apakah ada gambar dari frame_img (memory)
            if 'frame_img' in row and row['frame_img'] is not None:
                try:
                    small_img = cv2.resize(row['frame_img'], (240, 180))
                    b64_str = encode_image_to_base64(small_img)
                    if b64_str:
                        img_html = f'''
                        <img src="data:image/jpeg;base64,{b64_str}" 
                             style="width:240px; border-radius:8px; margin-top:8px; box-shadow: 0 2px 8px rgba(0,0,0,0.2);">
                        '''
                        print("✅ Using frame_img (memory)")
                except Exception as e:
                    print("❌ Error encoding frame_img:", e)
            
            # Atau dari image_path (database)
            elif 'image_path' in row and row['image_path']:
                print("Attempting to load from path:", row['image_path'])
                b64_str = load_image_from_path(row['image_path'])
                if b64_str:
                    img_html = f'''
                    <img src="data:image/jpeg;base64,{b64_str}" 
                         style="width:240px; border-radius:8px; margin-top:8px; box-shadow: 0 2px 8px rgba(0,0,0,0.2);">
                    '''
                    print("✅ Using image_path (database)")
                else:
                    print("❌ Failed to load image from path")
            
            # Severity badge color
            sev = row.get('severity', 'medium')
            sev_color = {'high': '#dc3545', 'medium': '#fd7e14', 'low': '#28a745'}.get(sev, '#6c757d')
            
            # Confidence
            conf = row.get('conf', 0)
            if isinstance(conf, (int, float)):
                conf_str = f"{conf:.1%}"
            else:
                conf_str = str(conf)
            
            # Build popup HTML
            popup_html = f"""
            <div style="font-family: 'Segoe UI', Arial, sans-serif; min-width: 260px; padding: 5px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h4 style="margin: 0; color: #333; font-size: 14px;">{row['type']}</h4>
                    <span style="background: {sev_color}; color: white; padding: 2px 8px; 
                                 border-radius: 10px; font-size: 11px; font-weight: 500;">
                        {sev.upper()}
                    </span>
                </div>
                <hr style="margin: 8px 0; border: none; border-top: 1px solid #eee;">
                <table style="font-size: 12px; color: #666; width: 100%;">
                    <tr><td>📍 Location</td><td style="text-align:right;">{row['lat']:.6f}, {row['lon']:.6f}</td></tr>
                    <tr><td>⏱️ Time</td><td style="text-align:right;">{row['timestamp']:.2f}s</td></tr>
                    <tr><td>🎯 Confidence</td><td style="text-align:right;">{conf_str}</td></tr>
                </table>
                {img_html}
            </div>
            """
            
            # Get marker color and icon
            marker_color = get_damage_color(row['type'], sev)
            marker_icon = get_damage_icon(row['type'])
            
            folium.Marker(
                location=[row['lat'], row['lon']],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"{row['type']} ({sev})",
                icon=folium.Icon(
                    color=marker_color, 
                    icon=marker_icon, 
                    prefix="fa"
                )
            ).add_to(marker_cluster)
    
    # Layer control
    folium.LayerControl().add_to(m)
    
    # Render map
    st_folium(m, width='stretch', height=500)
    
    # ==========================================
    # STATISTICS SUMMARY
    # ==========================================
    st.markdown("### 📊 Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric("Total Damages", len(df_filtered))
    
    # By severity
    sev_counts = df_filtered['severity'].value_counts()
    col2.metric("🔴 High Severity", sev_counts.get('high', 0))
    col3.metric("🟠 Medium Severity", sev_counts.get('medium', 0))
    col4.metric("🟢 Low Severity", sev_counts.get('low', 0))
    
    # Damage type breakdown
    st.markdown("#### Damage Type Distribution")
    type_counts = df_filtered['type'].value_counts()
    
    # Simple bar visualization
    for dtype, count in type_counts.items():
        pct = count / len(df_filtered) * 100
        col1, col2 = st.columns([3, 1])
        col1.progress(pct / 100, text=f"{dtype}")
        col2.write(f"{count} ({pct:.1f}%)")
    
    # ==========================================
    # DATA TABLE
    # ==========================================
    st.markdown("### 📋 Detailed Data")
    
    # Buat tampilan tabel yang lebih bersih
    display_df = df_filtered.drop(columns=['frame_img'], errors='ignore').copy()
    
    # Format columns
    if 'timestamp' in display_df.columns:
        display_df['timestamp'] = display_df['timestamp'].apply(lambda x: f"{x:.2f}s")
    if 'conf' in display_df.columns:
        display_df['conf'] = display_df['conf'].apply(
            lambda x: f"{x:.1%}" if isinstance(x, (int, float)) else x
        )
    if 'lat' in display_df.columns:
        display_df['lat'] = display_df['lat'].apply(lambda x: f"{x:.6f}")
    if 'lon' in display_df.columns:
        display_df['lon'] = display_df['lon'].apply(lambda x: f"{x:.6f}")
    
    st.dataframe(display_df, width='stretch', hide_index=True)


def render_history_map(db, session_id: str = None):
    """
    Render peta dari data history (database).
    
    Args:
        db: DamageDatabase instance
        session_id: Optional filter by session
    """
    if session_id:
        records = db.get_damages_by_session(session_id)
    else:
        records = db.get_all_damages(limit=500)
    
    if not records:
        st.info("No historical data available.")
        return
    
    # Convert records to list of dicts
    detections = []
    for rec in records:
        detections.append({
            'id': rec.id,
            'lat': rec.latitude,
            'lon': rec.longitude,
            'type': rec.damage_type,
            'timestamp': rec.timestamp,
            'conf': rec.confidence,
            'severity': rec.severity,
            'image_path': rec.image_path,
            'session_id': rec.session_id,
            'created_at': rec.created_at
        })
    
    render_analysis_map(detections, db=db, show_filters=True)
