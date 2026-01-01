"""
Real-time GPS Module for RoadGuard
Menggunakan streamlit-js-eval untuk bridge JavaScript GPS ke Python.
"""

import streamlit as st
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass
import time

# Try import streamlit-js-eval
try:
    from streamlit_js_eval import streamlit_js_eval, get_geolocation
    HAS_JS_EVAL = True
except ImportError:
    HAS_JS_EVAL = False


@dataclass
class GPSData:
    """Data GPS dari browser"""
    latitude: float
    longitude: float
    accuracy: float
    altitude: Optional[float] = None
    speed: Optional[float] = None
    heading: Optional[float] = None
    timestamp: float = 0.0


class RealtimeGPS:
    """
    GPS Realtime menggunakan HTML5 Geolocation API.
    
    Cara kerja:
    1. Menggunakan streamlit-js-eval untuk menjalankan JavaScript
    2. JavaScript memanggil navigator.geolocation.getCurrentPosition()
    3. Data dikembalikan ke Python
    
    Catatan:
    - Memerlukan HTTPS atau localhost
    - User harus memberikan permission lokasi
    - Akurasi tergantung device (HP lebih akurat dari laptop)
    """
    
    def __init__(self):
        self._last_data: Optional[GPSData] = None
        self._last_update: float = 0
        self._cache_duration: float = 1.0  # Cache selama 1 detik
        self._fallback_lat: float = -6.9024
        self._fallback_lon: float = 107.6188
        
        # Initialize session state
        if 'realtime_gps_enabled' not in st.session_state:
            st.session_state['realtime_gps_enabled'] = False
        if 'realtime_gps_data' not in st.session_state:
            st.session_state['realtime_gps_data'] = None
        if 'realtime_gps_error' not in st.session_state:
            st.session_state['realtime_gps_error'] = None
    
    @staticmethod
    def is_available() -> bool:
        """Cek apakah streamlit-js-eval tersedia"""
        return HAS_JS_EVAL
    
    def get_location(self) -> Tuple[float, float, float]:
        """
        Dapatkan lokasi GPS saat ini dari browser.
        
        Returns:
            Tuple (latitude, longitude, accuracy)
            Jika gagal, return fallback location dengan accuracy -1
        """
        if not HAS_JS_EVAL:
            st.session_state['realtime_gps_error'] = "streamlit-js-eval not installed"
            return self._fallback_lat, self._fallback_lon, -1
        
        # Check cache
        current_time = time.time()
        if self._last_data and (current_time - self._last_update) < self._cache_duration:
            return self._last_data.latitude, self._last_data.longitude, self._last_data.accuracy
        
        try:
            # Gunakan get_geolocation dari streamlit-js-eval
            location = get_geolocation()
            
            if location and 'coords' in location:
                coords = location['coords']
                
                self._last_data = GPSData(
                    latitude=coords.get('latitude', self._fallback_lat),
                    longitude=coords.get('longitude', self._fallback_lon),
                    accuracy=coords.get('accuracy', 0),
                    altitude=coords.get('altitude'),
                    speed=coords.get('speed'),
                    heading=coords.get('heading'),
                    timestamp=location.get('timestamp', current_time * 1000)
                )
                self._last_update = current_time
                
                # Update session state
                st.session_state['realtime_gps_data'] = {
                    'lat': self._last_data.latitude,
                    'lon': self._last_data.longitude,
                    'accuracy': self._last_data.accuracy,
                    'speed': self._last_data.speed,
                    'heading': self._last_data.heading,
                    'timestamp': self._last_data.timestamp
                }
                st.session_state['realtime_gps_error'] = None
                st.session_state['realtime_gps_enabled'] = True
                
                return self._last_data.latitude, self._last_data.longitude, self._last_data.accuracy
            
            else:
                # Lokasi belum tersedia, mungkin masih request permission
                st.session_state['realtime_gps_error'] = "Waiting for GPS permission..."
                
                # Return last known atau fallback
                if self._last_data:
                    return self._last_data.latitude, self._last_data.longitude, self._last_data.accuracy
                return self._fallback_lat, self._fallback_lon, -1
                
        except Exception as e:
            st.session_state['realtime_gps_error'] = str(e)
            
            if self._last_data:
                return self._last_data.latitude, self._last_data.longitude, self._last_data.accuracy
            return self._fallback_lat, self._fallback_lon, -1
    
    def get_location_simple(self) -> Tuple[float, float]:
        """
        Dapatkan lokasi GPS (latitude, longitude) saja.
        
        Returns:
            Tuple (latitude, longitude)
        """
        lat, lon, _ = self.get_location()
        return lat, lon
    
    def set_fallback(self, lat: float, lon: float):
        """Set lokasi fallback jika GPS tidak tersedia"""
        self._fallback_lat = lat
        self._fallback_lon = lon
    
    def get_status(self) -> Dict[str, Any]:
        """Dapatkan status GPS"""
        return {
            'enabled': st.session_state.get('realtime_gps_enabled', False),
            'error': st.session_state.get('realtime_gps_error'),
            'last_data': st.session_state.get('realtime_gps_data'),
            'has_js_eval': HAS_JS_EVAL
        }


def render_gps_status_widget():
    """Render widget status GPS di sidebar atau main page"""
    gps = RealtimeGPS()
    status = gps.get_status()
    
    if not status['has_js_eval']:
        st.warning("⚠️ Install `streamlit-js-eval` untuk GPS realtime")
        st.code("pip install streamlit-js-eval", language="bash")
        return
    
    if status['enabled'] and status['last_data']:
        data = status['last_data']
        st.success(f"📍 GPS Active")
        
        col1, col2 = st.columns(2)
        col1.metric("Latitude", f"{data['lat']:.6f}")
        col2.metric("Longitude", f"{data['lon']:.6f}")
        
        if data.get('accuracy'):
            st.caption(f"Accuracy: {data['accuracy']:.1f}m")
        if data.get('speed'):
            st.caption(f"Speed: {data['speed'] * 3.6:.1f} km/h")
    
    elif status['error']:
        st.error(f"📍 GPS Error: {status['error']}")
    
    else:
        st.info("📍 GPS: Waiting for permission...")


# ============================================
# Alternative: Manual JavaScript dengan polling
# ============================================

def get_gps_with_javascript() -> Optional[Dict]:
    """
    Alternatif menggunakan raw JavaScript execution.
    Gunakan jika get_geolocation tidak bekerja.
    """
    if not HAS_JS_EVAL:
        return None
    
    js_code = """
    new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            resolve({error: 'Geolocation not supported'});
            return;
        }
        
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                resolve({
                    latitude: pos.coords.latitude,
                    longitude: pos.coords.longitude,
                    accuracy: pos.coords.accuracy,
                    altitude: pos.coords.altitude,
                    speed: pos.coords.speed,
                    heading: pos.coords.heading,
                    timestamp: pos.timestamp
                });
            },
            (err) => {
                resolve({error: err.message, code: err.code});
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 5000
            }
        );
    });
    """
    
    try:
        result = streamlit_js_eval(js_expressions=js_code, want_output=True, key="gps_fetch")
        return result
    except:
        return None


# Singleton instance
_realtime_gps_instance: Optional[RealtimeGPS] = None

def get_realtime_gps() -> RealtimeGPS:
    """Get singleton instance of RealtimeGPS"""
    global _realtime_gps_instance
    if _realtime_gps_instance is None:
        _realtime_gps_instance = RealtimeGPS()
    return _realtime_gps_instance


# ============================================
# HTML Component for GPS Display
# ============================================

def create_gps_component_html(key: str = "gps") -> str:
    """
    Create HTML component for GPS display.
    This renders a visual GPS status widget.
    """
    return f"""
    <style>
        .gps-container {{
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border-radius: 12px;
            padding: 15px;
            color: white;
            border: 1px solid #0f3460;
        }}
        .gps-header {{
            display: flex;
            align-items: center;
            margin-bottom: 10px;
        }}
        .gps-status {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
            animation: pulse 2s infinite;
        }}
        .gps-active {{ background: #00ff88; }}
        .gps-waiting {{ background: #ffcc00; }}
        .gps-error {{ background: #ff4444; }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        .gps-coords {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-top: 10px;
        }}
        .gps-coord-item {{
            background: rgba(255,255,255,0.1);
            padding: 8px;
            border-radius: 6px;
            text-align: center;
        }}
        .gps-coord-label {{
            font-size: 10px;
            color: #aaa;
            margin-bottom: 4px;
        }}
        .gps-coord-value {{
            font-size: 14px;
            font-weight: bold;
            font-family: monospace;
        }}
    </style>
    
    <div class="gps-container" id="gps-widget-{key}">
        <div class="gps-header">
            <div class="gps-status gps-waiting" id="gps-indicator-{key}"></div>
            <span id="gps-status-text-{key}">Requesting GPS...</span>
        </div>
        <div class="gps-coords">
            <div class="gps-coord-item">
                <div class="gps-coord-label">LATITUDE</div>
                <div class="gps-coord-value" id="gps-lat-{key}">--</div>
            </div>
            <div class="gps-coord-item">
                <div class="gps-coord-label">LONGITUDE</div>
                <div class="gps-coord-value" id="gps-lon-{key}">--</div>
            </div>
        </div>
    </div>
    
    <script>
    (function() {{
        const key = "{key}";
        const indicator = document.getElementById(`gps-indicator-${{key}}`);
        const statusText = document.getElementById(`gps-status-text-${{key}}`);
        const latEl = document.getElementById(`gps-lat-${{key}}`);
        const lonEl = document.getElementById(`gps-lon-${{key}}`);
        
        if (!navigator.geolocation) {{
            indicator.className = 'gps-status gps-error';
            statusText.textContent = 'GPS not supported';
            return;
        }}
        
        function updatePosition(pos) {{
            indicator.className = 'gps-status gps-active';
            statusText.textContent = 'GPS Active';
            latEl.textContent = pos.coords.latitude.toFixed(6);
            lonEl.textContent = pos.coords.longitude.toFixed(6);
        }}
        
        function handleError(err) {{
            indicator.className = 'gps-status gps-error';
            statusText.textContent = 'GPS Error: ' + err.message;
        }}
        
        // Initial request
        navigator.geolocation.getCurrentPosition(updatePosition, handleError, {{
            enableHighAccuracy: true,
            timeout: 10000
        }});
        
        // Watch for updates
        navigator.geolocation.watchPosition(updatePosition, handleError, {{
            enableHighAccuracy: true,
            maximumAge: 5000
        }});
    }})();
    </script>
    """


def render_realtime_gps(placeholder=None):
    """
    Render realtime GPS and return current location.
    Uses streamlit-js-eval to fetch GPS from browser.
    
    Returns:
        Tuple[float, float] or None: (latitude, longitude) or None if unavailable
    """
    gps = get_realtime_gps()
    location = gps.get_location()
    
    if location:
        return location
    return None