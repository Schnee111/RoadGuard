"""
Real-time GPS Module for RoadGuard
Menggunakan HTML5 Geolocation API melalui JavaScript injection di Streamlit.
Bisa digunakan dari HP atau Laptop yang memiliki GPS/lokasi.
"""

import streamlit as st
import streamlit.components.v1 as components
import json
import time
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import threading
import queue


@dataclass
class RealtimeGPSPoint:
    """Data point GPS real-time"""
    latitude: float
    longitude: float
    accuracy: float  # dalam meter
    altitude: Optional[float] = None
    altitude_accuracy: Optional[float] = None
    heading: Optional[float] = None  # arah dalam derajat
    speed: Optional[float] = None  # m/s
    timestamp: float = 0.0


class RealtimeGPSManager:
    """
    Manager untuk GPS real-time menggunakan browser Geolocation API.
    
    Cara kerja:
    1. Inject JavaScript ke halaman Streamlit
    2. JavaScript memanggil navigator.geolocation.watchPosition()
    3. Data dikirim ke Streamlit via st.session_state
    
    Kompatibilitas:
    - Chrome, Firefox, Safari, Edge (desktop & mobile)
    - Memerlukan HTTPS atau localhost
    - User harus memberikan permission
    """
    
    def __init__(self):
        self.is_active = False
        self.last_position: Optional[RealtimeGPSPoint] = None
        self.position_history: list = []
        self.error_message: Optional[str] = None
        
        # Initialize session state keys
        if 'realtime_gps_data' not in st.session_state:
            st.session_state['realtime_gps_data'] = None
        if 'realtime_gps_error' not in st.session_state:
            st.session_state['realtime_gps_error'] = None
        if 'realtime_gps_active' not in st.session_state:
            st.session_state['realtime_gps_active'] = False
    
    def render_gps_component(self, high_accuracy: bool = True, 
                             max_age: int = 5000,
                             timeout: int = 10000) -> None:
        """
        Render komponen JavaScript untuk GPS tracking.
        
        Args:
            high_accuracy: Gunakan GPS hardware (lebih akurat tapi lebih lambat)
            max_age: Maksimal umur cache posisi (ms)
            timeout: Timeout untuk mendapatkan posisi (ms)
        """
        
        gps_js = f"""
        <div id="gps-status" style="
            padding: 10px; 
            border-radius: 8px; 
            background: rgba(0,0,0,0.3);
            color: #fff;
            font-family: monospace;
            font-size: 12px;
            margin: 5px 0;
        ">
            <div id="gps-indicator" style="display: flex; align-items: center; gap: 8px;">
                <span id="gps-dot" style="
                    width: 10px; 
                    height: 10px; 
                    border-radius: 50%; 
                    background: #666;
                    animation: none;
                "></span>
                <span id="gps-text">GPS: Initializing...</span>
            </div>
            <div id="gps-coords" style="margin-top: 5px; display: none;">
                <div>📍 Lat: <span id="lat-val">-</span></div>
                <div>📍 Lon: <span id="lon-val">-</span></div>
                <div>🎯 Accuracy: <span id="acc-val">-</span></div>
                <div>🧭 Heading: <span id="head-val">-</span></div>
                <div>🚗 Speed: <span id="speed-val">-</span></div>
            </div>
        </div>
        
        <style>
            @keyframes pulse {{
                0% {{ opacity: 1; }}
                50% {{ opacity: 0.5; }}
                100% {{ opacity: 1; }}
            }}
            .gps-active {{
                background: #00ff00 !important;
                animation: pulse 1s infinite !important;
            }}
            .gps-error {{
                background: #ff4444 !important;
            }}
        </style>
        
        <script>
        (function() {{
            const dot = document.getElementById('gps-dot');
            const text = document.getElementById('gps-text');
            const coords = document.getElementById('gps-coords');
            const latVal = document.getElementById('lat-val');
            const lonVal = document.getElementById('lon-val');
            const accVal = document.getElementById('acc-val');
            const headVal = document.getElementById('head-val');
            const speedVal = document.getElementById('speed-val');
            
            // Check if geolocation is supported
            if (!navigator.geolocation) {{
                dot.className = 'gps-error';
                text.textContent = 'GPS: Not supported in this browser';
                sendToStreamlit(null, 'Geolocation not supported');
                return;
            }}
            
            // Function to send data to Streamlit
            function sendToStreamlit(data, error) {{
                // Use postMessage to communicate with Streamlit
                const message = {{
                    type: 'streamlit:gps_update',
                    data: data,
                    error: error
                }};
                
                // Store in a hidden element that Streamlit can read
                let dataEl = document.getElementById('gps-data-store');
                if (!dataEl) {{
                    dataEl = document.createElement('div');
                    dataEl.id = 'gps-data-store';
                    dataEl.style.display = 'none';
                    document.body.appendChild(dataEl);
                }}
                dataEl.setAttribute('data-gps', JSON.stringify(message));
                
                // Dispatch custom event
                window.dispatchEvent(new CustomEvent('gps_update', {{ detail: message }}));
            }}
            
            // Success callback
            function onSuccess(position) {{
                const data = {{
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    accuracy: position.coords.accuracy,
                    altitude: position.coords.altitude,
                    altitudeAccuracy: position.coords.altitudeAccuracy,
                    heading: position.coords.heading,
                    speed: position.coords.speed,
                    timestamp: position.timestamp
                }};
                
                // Update UI
                dot.className = 'gps-active';
                text.textContent = 'GPS: Active ✓';
                coords.style.display = 'block';
                latVal.textContent = data.latitude.toFixed(6);
                lonVal.textContent = data.longitude.toFixed(6);
                accVal.textContent = data.accuracy.toFixed(1) + ' m';
                headVal.textContent = data.heading ? data.heading.toFixed(1) + '°' : 'N/A';
                speedVal.textContent = data.speed ? (data.speed * 3.6).toFixed(1) + ' km/h' : 'N/A';
                
                sendToStreamlit(data, null);
            }}
            
            // Error callback
            function onError(error) {{
                let errorMsg = 'Unknown error';
                switch(error.code) {{
                    case error.PERMISSION_DENIED:
                        errorMsg = 'Permission denied. Please allow location access.';
                        break;
                    case error.POSITION_UNAVAILABLE:
                        errorMsg = 'Position unavailable. Check GPS/Location settings.';
                        break;
                    case error.TIMEOUT:
                        errorMsg = 'Request timeout. Retrying...';
                        break;
                }}
                
                dot.className = 'gps-error';
                text.textContent = 'GPS: ' + errorMsg;
                
                sendToStreamlit(null, errorMsg);
            }}
            
            // Options
            const options = {{
                enableHighAccuracy: {str(high_accuracy).lower()},
                maximumAge: {max_age},
                timeout: {timeout}
            }};
            
            // Start watching position
            text.textContent = 'GPS: Requesting permission...';
            
            const watchId = navigator.geolocation.watchPosition(
                onSuccess,
                onError,
                options
            );
            
            // Store watch ID for cleanup
            window.gpsWatchId = watchId;
            
            // Cleanup on page unload
            window.addEventListener('beforeunload', function() {{
                if (window.gpsWatchId) {{
                    navigator.geolocation.clearWatch(window.gpsWatchId);
                }}
            }});
        }})();
        </script>
        """
        
        components.html(gps_js, height=150)
    
    def render_gps_receiver(self) -> Optional[Dict[str, Any]]:
        """
        Render komponen tersembunyi untuk menerima data GPS dari JavaScript.
        Menggunakan teknik JavaScript-to-Python bridge.
        
        Returns:
            Dictionary dengan data GPS atau None
        """
        
        # JavaScript yang akan membaca data dan mengirim ke Streamlit
        receiver_js = """
        <div id="gps-receiver" style="display:none;"></div>
        <script>
        (function() {
            // Poll for GPS data
            function checkGPSData() {
                const dataEl = document.getElementById('gps-data-store');
                if (dataEl) {
                    const data = dataEl.getAttribute('data-gps');
                    if (data) {
                        // Send to Streamlit via query params trick
                        const parsed = JSON.parse(data);
                        if (parsed.data) {
                            // Store in sessionStorage for Streamlit to read
                            sessionStorage.setItem('gps_data', JSON.stringify(parsed.data));
                        }
                    }
                }
                setTimeout(checkGPSData, 500);
            }
            checkGPSData();
        })();
        </script>
        """
        
        components.html(receiver_js, height=0)
        return st.session_state.get('realtime_gps_data')
    
    def get_current_position(self) -> Optional[RealtimeGPSPoint]:
        """Dapatkan posisi GPS terkini dari session state"""
        data = st.session_state.get('realtime_gps_data')
        
        if data:
            return RealtimeGPSPoint(
                latitude=data.get('latitude', 0),
                longitude=data.get('longitude', 0),
                accuracy=data.get('accuracy', 0),
                altitude=data.get('altitude'),
                altitude_accuracy=data.get('altitudeAccuracy'),
                heading=data.get('heading'),
                speed=data.get('speed'),
                timestamp=data.get('timestamp', time.time() * 1000)
            )
        return None


def render_realtime_gps_widget(container=None) -> Tuple[Optional[float], Optional[float]]:
    """
    Render widget GPS real-time yang simple.
    
    Args:
        container: Streamlit container untuk render (optional)
    
    Returns:
        Tuple (latitude, longitude) atau (None, None) jika belum ada data
    """
    
    target = container if container else st
    
    # JavaScript untuk GPS
    gps_html = """
    <div id="realtime-gps-widget" style="
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid rgba(0, 229, 255, 0.3);
        border-radius: 10px;
        padding: 15px;
        font-family: 'Segoe UI', sans-serif;
    ">
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
            <div id="status-indicator" style="
                width: 12px;
                height: 12px;
                border-radius: 50%;
                background: #666;
            "></div>
            <span style="color: #00e5ff; font-weight: 600;">Real-time GPS</span>
        </div>
        
        <div id="gps-display" style="color: #e0e0e0; font-size: 14px;">
            <div style="display: flex; justify-content: space-between; margin: 5px 0;">
                <span>Latitude:</span>
                <span id="rt-lat" style="color: #00ff88; font-family: monospace;">Waiting...</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin: 5px 0;">
                <span>Longitude:</span>
                <span id="rt-lon" style="color: #00ff88; font-family: monospace;">Waiting...</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin: 5px 0;">
                <span>Accuracy:</span>
                <span id="rt-acc" style="color: #ffaa00; font-family: monospace;">-</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin: 5px 0;">
                <span>Speed:</span>
                <span id="rt-speed" style="color: #ff88ff; font-family: monospace;">-</span>
            </div>
        </div>
        
        <div id="gps-error" style="
            display: none;
            color: #ff6b6b;
            font-size: 12px;
            margin-top: 10px;
            padding: 8px;
            background: rgba(255, 0, 0, 0.1);
            border-radius: 5px;
        "></div>
        
        <!-- Hidden input untuk transfer data ke Streamlit -->
        <input type="hidden" id="gps-lat-input" value="">
        <input type="hidden" id="gps-lon-input" value="">
    </div>
    
    <style>
        @keyframes gps-pulse {
            0%, 100% { opacity: 1; box-shadow: 0 0 5px #00ff00; }
            50% { opacity: 0.7; box-shadow: 0 0 15px #00ff00; }
        }
        .gps-active-indicator {
            background: #00ff00 !important;
            animation: gps-pulse 1.5s ease-in-out infinite;
        }
    </style>
    
    <script>
    (function() {
        const indicator = document.getElementById('status-indicator');
        const latEl = document.getElementById('rt-lat');
        const lonEl = document.getElementById('rt-lon');
        const accEl = document.getElementById('rt-acc');
        const speedEl = document.getElementById('rt-speed');
        const errorEl = document.getElementById('gps-error');
        const latInput = document.getElementById('gps-lat-input');
        const lonInput = document.getElementById('gps-lon-input');
        
        if (!navigator.geolocation) {
            errorEl.style.display = 'block';
            errorEl.textContent = '⚠️ Geolocation is not supported by this browser.';
            indicator.style.background = '#ff4444';
            return;
        }
        
        function updatePosition(position) {
            const lat = position.coords.latitude;
            const lon = position.coords.longitude;
            const acc = position.coords.accuracy;
            const speed = position.coords.speed;
            
            // Update display
            latEl.textContent = lat.toFixed(6);
            lonEl.textContent = lon.toFixed(6);
            accEl.textContent = acc.toFixed(1) + ' m';
            speedEl.textContent = speed ? (speed * 3.6).toFixed(1) + ' km/h' : '0 km/h';
            
            // Update indicator
            indicator.className = 'gps-active-indicator';
            
            // Store in hidden inputs
            latInput.value = lat.toString();
            lonInput.value = lon.toString();
            
            // Store in window for external access
            window.currentGPSLat = lat;
            window.currentGPSLon = lon;
            window.currentGPSAcc = acc;
            window.currentGPSSpeed = speed || 0;
            window.currentGPSTimestamp = position.timestamp;
            
            // Store in sessionStorage
            sessionStorage.setItem('realtime_gps', JSON.stringify({
                lat: lat,
                lon: lon,
                accuracy: acc,
                speed: speed,
                timestamp: position.timestamp
            }));
            
            errorEl.style.display = 'none';
        }
        
        function handleError(error) {
            indicator.style.background = '#ff4444';
            errorEl.style.display = 'block';
            
            switch(error.code) {
                case error.PERMISSION_DENIED:
                    errorEl.innerHTML = '⚠️ <b>Permission Denied</b><br>Please allow location access in your browser settings.';
                    break;
                case error.POSITION_UNAVAILABLE:
                    errorEl.innerHTML = '⚠️ <b>Position Unavailable</b><br>Make sure GPS/Location is enabled on your device.';
                    break;
                case error.TIMEOUT:
                    errorEl.innerHTML = '⚠️ <b>Timeout</b><br>Could not get location. Retrying...';
                    // Retry after timeout
                    setTimeout(startTracking, 2000);
                    break;
            }
        }
        
        function startTracking() {
            navigator.geolocation.watchPosition(
                updatePosition,
                handleError,
                {
                    enableHighAccuracy: true,
                    maximumAge: 2000,
                    timeout: 10000
                }
            );
        }
        
        // Start tracking
        latEl.textContent = 'Requesting...';
        lonEl.textContent = 'Requesting...';
        startTracking();
    })();
    </script>
    """
    
    target.components.html(gps_html, height=200)
    
    # Return current GPS dari session state (akan di-update oleh JavaScript)
    gps_data = st.session_state.get('realtime_gps_data')
    if gps_data:
        return gps_data.get('lat'), gps_data.get('lon')
    return None, None


class BrowserGPSBridge:
    """
    Bridge antara JavaScript GPS dan Python.
    Menggunakan teknik polling untuk mendapatkan data GPS dari browser.
    """
    
    def __init__(self):
        self._init_session_state()
    
    def _init_session_state(self):
        """Initialize session state untuk GPS data"""
        if 'browser_gps_lat' not in st.session_state:
            st.session_state['browser_gps_lat'] = None
        if 'browser_gps_lon' not in st.session_state:
            st.session_state['browser_gps_lon'] = None
        if 'browser_gps_accuracy' not in st.session_state:
            st.session_state['browser_gps_accuracy'] = None
        if 'browser_gps_timestamp' not in st.session_state:
            st.session_state['browser_gps_timestamp'] = None
    
    def render_and_get_location(self) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Render GPS component dan dapatkan lokasi terkini.
        
        Returns:
            Tuple (latitude, longitude, accuracy) atau (None, None, None)
        """
        
        # Gunakan st.components untuk inject JavaScript
        gps_component = """
        <script>
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                function(pos) {
                    // Simpan ke parent window
                    window.parent.postMessage({
                        type: 'gps_update',
                        lat: pos.coords.latitude,
                        lon: pos.coords.longitude,
                        accuracy: pos.coords.accuracy
                    }, '*');
                },
                function(err) {
                    window.parent.postMessage({
                        type: 'gps_error',
                        error: err.message
                    }, '*');
                },
                {enableHighAccuracy: true}
            );
        }
        </script>
        """
        
        components.html(gps_component, height=0)
        
        return (
            st.session_state.get('browser_gps_lat'),
            st.session_state.get('browser_gps_lon'),
            st.session_state.get('browser_gps_accuracy')
        )