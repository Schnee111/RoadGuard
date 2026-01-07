# 🛡️ RoadGuard Vision

**AI-Powered Road Damage Detection System with Real-time GPS Tracking**

RoadGuard Vision adalah sistem deteksi kerusakan jalan berbasis kecerdasan buatan (AI) yang menggunakan YOLOv8 untuk mendeteksi berbagai jenis kerusakan jalan secara real-time. Sistem ini dilengkapi dengan integrasi GPS untuk pemetaan lokasi kerusakan dan dashboard interaktif untuk visualisasi data.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)
![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## 📋 Daftar Isi

- [Fitur Utama](#-fitur-utama)
- [Jenis Kerusakan yang Terdeteksi](#-jenis-kerusakan-yang-terdeteksi)
- [Teknologi yang Digunakan](#-teknologi-yang-digunakan)
- [Struktur Project](#-struktur-project)
- [Instalasi](#-instalasi)
- [Cara Penggunaan](#-cara-penggunaan)
- [Konfigurasi](#%EF%B8%8F-konfigurasi)
- [Arsitektur Sistem](#-arsitektur-sistem)
- [Fitur GPS](#-fitur-gps)
- [Export Data](#-export-data)
- [Tracking System](#-tracking-system)
- [Database](#-database)
- [Troubleshooting](#-troubleshooting)
- [Kontribusi](#-kontribusi)
- [Lisensi](#-lisensi)

---

## 🌟 Fitur Utama

### 1. **Deteksi Kerusakan Real-time**
- Menggunakan model YOLOv8 yang dilatih pada dataset RDD (Road Damage Detection)
- Deteksi multi-class untuk berbagai jenis kerusakan jalan
- Confidence threshold yang dapat disesuaikan
- Visualisasi bounding box dengan label dan confidence score

### 2. **Multi-Source Video Input**
- **File Video**: Upload video hasil rekaman (.mp4, .avi, .mov)
- **Webcam**: Gunakan kamera laptop/komputer
- **RTSP/IP Camera**: Koneksi ke kamera IP atau CCTV
- **Browser Camera**: Gunakan kamera smartphone melalui browser (WebRTC)

### 3. **Integrasi GPS Komprehensif**
- **Realtime GPS**: Menggunakan GPS dari browser (smartphone/tablet)
- **Simulasi GPS**: Untuk testing tanpa perangkat GPS
- **Upload CSV/GPX**: Import data GPS dari file
- **Manual Input**: Input koordinat secara manual

### 4. **Advanced Tracking System**
- ByteTrack algorithm untuk tracking objek
- IoU-based matching untuk menghindari duplikasi deteksi
- Konfigurasi IoU threshold dan minimum hits
- Minimum distance filtering untuk deteksi yang terlalu dekat

### 5. **Dashboard Interaktif**
- Panel statistik real-time
- Visualisasi video dengan deteksi overlay
- Progress bar untuk pemrosesan video
- Session summary dengan metrik lengkap

### 6. **Peta Interaktif**
- Live map dengan marker real-time
- Heatmap untuk visualisasi konsentrasi kerusakan
- Filter berdasarkan jenis kerusakan dan tingkat keparahan
- Cluster markers untuk performa optimal

### 7. **Export Data**
- **CSV**: Export data tabulasi untuk analisis
- **GeoJSON**: Format standar untuk aplikasi GIS
- **KML**: Kompatibel dengan Google Earth
- **PDF Report**: Laporan lengkap dengan peta dan statistik (opsional)

### 8. **Database Persistent**
- SQLite database untuk penyimpanan data
- Riwayat inspeksi lengkap
- Query dan analisis data historis
- Session management

---

## 🔍 Jenis Kerusakan yang Terdeteksi

| Kode | Jenis Kerusakan | Deskripsi | Severity |
|------|----------------|-----------|----------|
| **D00** | Longitudinal Crack | Retakan memanjang searah jalan | Medium |
| **D10** | Transverse Crack | Retakan melintang tegak lurus jalan | Medium |
| **D20** | Alligator Crack | Retakan seperti kulit buaya (fatigue crack) | High |
| **D40** | Pothole | Lubang pada permukaan jalan | High |
| **D43** | Damaged Lane Marking | Marka jalan rusak | Low |
| **D44** | Faded Lane Marking | Marka jalan pudar/hilang | Low |

### Klasifikasi Severity
- 🔴 **High**: Kerusakan serius memerlukan perbaikan segera (Pothole, Alligator Crack)
- 🟠 **Medium**: Kerusakan perlu perhatian (Longitudinal/Transverse Crack)
- 🟢 **Low**: Kerusakan minor (Lane Marking issues)

---

## 🛠 Teknologi yang Digunakan

### Core Framework
- **Python 3.8+**: Bahasa pemrograman utama
- **Streamlit 1.28+**: Framework web application
- **SQLite**: Database untuk penyimpanan data

### Computer Vision & AI
- **Ultralytics YOLOv8**: Object detection model
- **OpenCV**: Image processing dan video handling
- **NumPy**: Numerical computing
- **Pillow**: Image manipulation

### Mapping & Geospatial
- **Folium**: Interactive map visualization
- **Streamlit-Folium**: Streamlit integration untuk Folium

### Data Processing
- **Pandas**: Data manipulation dan analysis
- **SciPy**: Scientific computing (Hungarian algorithm untuk tracking)

### Real-time Features
- **Streamlit-WebRTC**: Browser camera access
- **Streamlit-JS-Eval**: Real-time GPS dari browser
- **AV**: Audio/video processing untuk WebRTC

---

## 📁 Struktur Project

```
RoadGuard/
│
├── src/
│   ├── app.py                      # Main application entry point
│   │
│   ├── components/                 # UI Components
│   │   ├── dashboard.py           # Dashboard & metrics
│   │   ├── export.py              # Export functionality
│   │   ├── map_view.py            # Map visualization
│   │   ├── sidebar.py             # Sidebar controls
│   │   └── styling.py             # CSS styling
│   │
│   ├── models/                    # YOLO Models
│   │   ├── YOLOv8_Small_RDD.pt   # RDD trained model
│   │   └── yolov8n.pt            # Base YOLOv8 nano
│   │
│   └── modules/                   # Core Modules
│       ├── detector.py            # Road damage detector
│       ├── gps_manager.py         # GPS data management
│       ├── database.py            # SQLite database handler
│       ├── bytetrack.py           # ByteTrack tracking algorithm
│       ├── browser_camera.py      # WebRTC camera support
│       ├── gps_simulation.py      # GPS simulation
│       └── realtime_gps.py        # Real-time GPS from browser
│
├── results/                       # Output Directory
│   ├── evidence/                 # Detection screenshots
│   ├── videos/                   # Processed videos
│   └── roadguard.db             # SQLite database
│
├── sample_gps/                   # Sample GPS Files
│   ├── route_pothole-2.csv
│   └── route_upi.csv
│
├── video/                        # Sample Videos (optional)
│
├── requirements.txt              # Python dependencies
├── packages.txt                  # System packages (untuk deployment)
└── README.md                     # Documentation (this file)
```

---

## 🚀 Instalasi

### Prerequisites

- Python 3.8 atau lebih tinggi
- pip (Python package manager)
- Git (untuk clone repository)
- Webcam (opsional, untuk input kamera)

### Langkah Instalasi

1. **Clone Repository**
```bash
git clone https://github.com/yourusername/roadguard-vision.git
cd roadguard-vision
```

2. **Buat Virtual Environment** (Rekomendasi)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

4. **Verifikasi Instalasi**
```bash
python -c "import streamlit; import cv2; import ultralytics; print('Installation successful!')"
```

5. **Download Model YOLOv8** (jika belum ada)
- Model RDD sudah included di `src/models/YOLOv8_Small_RDD.pt`
- Atau download model custom Anda dan letakkan di folder `src/models/`

---

## 📖 Cara Penggunaan

### 1. Menjalankan Aplikasi

```bash
cd src
streamlit run app.py
```

Aplikasi akan terbuka di browser pada `http://localhost:8501`

### 2. Workflow Deteksi

#### **Mode Inspection (Real-time Detection)**

1. **Pilih Source Video**
   - Di sidebar, pilih "Video Source"
   - Options: File Upload, Webcam, RTSP, Browser Camera

2. **Konfigurasi GPS**
   - Pilih "GPS Mode": Simulation, Realtime, CSV Upload, Manual
   - Untuk Realtime GPS: Izinkan akses lokasi di browser

3. **Atur Parameter Deteksi**
   - **Confidence Threshold**: 0.1 - 1.0 (default: 0.35)
   - **IoU Threshold**: 0.1 - 0.9 (tracking)
   - **Minimum Hits**: Jumlah frame untuk konfirmasi deteksi
   - **Min Distance**: Jarak minimum antar deteksi (meter)

4. **Start Detection**
   - Klik tombol "▶️ Start Inspection"
   - Monitor real-time metrics di dashboard
   - Lihat deteksi pada live map

5. **Stop & Review**
   - Klik "⏹️ Stop Inspection"
   - Review session summary
   - Export data jika diperlukan

#### **Mode History (Data Review)**

1. **Pilih Session**
   - Switch ke tab "📁 History"
   - Pilih session dari dropdown

2. **Analisis Data**
   - Lihat peta dengan semua deteksi
   - Filter berdasarkan jenis kerusakan
   - Analisis statistik session

3. **Export**
   - Pilih format export (CSV, GeoJSON, KML)
   - Download hasil analisis

---

## ⚙️ Konfigurasi

### Model Configuration

Edit di `src/app.py`:

```python
MODEL_PATH = "models/YOLOv8_Small_RDD.pt"  # Path model
CONFIDENCE_THRESHOLD = 0.35                 # Default confidence
```

### GPS Configuration

Edit di `src/modules/gps_manager.py`:

```python
# Default start position (Bandung)
DEFAULT_LAT = -6.9024
DEFAULT_LON = 107.6188

# Simulation speed
SIMULATION_SPEED = 0.0005  # degrees per frame
```

### Tracking Configuration

```python
# IoU Tracker Settings
IOU_THRESHOLD = 0.3        # IoU threshold untuk matching
MIN_HITS = 2               # Minimum frames untuk track
MIN_DISTANCE = 5.0         # Minimum distance (meter)
```

### Database Configuration

```python
DB_PATH = "results/roadguard.db"
```

---

## 🏗 Arsitektur Sistem

### System Flow

```
┌─────────────┐
│ Video Input │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  Frame Extract  │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐      ┌──────────────┐
│  YOLO Detection │◄─────┤  Model Load  │
└──────┬──────────┘      └──────────────┘
       │
       ▼
┌─────────────────┐
│  ByteTrack IoU  │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐      ┌──────────────┐
│  GPS Matching   │◄─────┤  GPS Manager │
└──────┬──────────┘      └──────────────┘
       │
       ▼
┌─────────────────┐
│  Save Database  │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  Live Dashboard │
└─────────────────┘
```

### Module Dependencies

```
app.py
├── components/
│   ├── dashboard.py      → metrics visualization
│   ├── map_view.py       → folium maps
│   ├── sidebar.py        → user controls
│   └── export.py         → data export
│
└── modules/
    ├── detector.py       → YOLOv8 inference
    ├── bytetrack.py      → object tracking
    ├── gps_manager.py    → GPS handling
    ├── database.py       → SQLite operations
    └── realtime_gps.py   → browser GPS
```

---

## 🌍 Fitur GPS

### 1. Realtime GPS (Recommended)

Menggunakan GPS dari smartphone/tablet melalui browser:

**Setup:**
- Buka aplikasi di smartphone
- Izinkan akses lokasi di browser
- Pilih "Realtime GPS" di sidebar

**Kelebihan:**
- Akurasi tinggi
- Update real-time
- Tidak perlu file eksternal

**Catatan:**
- Memerlukan HTTPS atau localhost
- Browser harus support Geolocation API

### 2. Simulation Mode

Untuk testing tanpa GPS device:

```python
# Route predefined
route = [
    (-6.9024, 107.6188),  # Start
    (-6.9030, 107.6195),  # Point 2
    # ... more points
]
```

### 3. CSV Upload

Format CSV yang didukung:

```csv
latitude,longitude,timestamp
-6.9024,107.6188,2026-01-08 10:00:00
-6.9030,107.6195,2026-01-08 10:00:05
```

### 4. GPX Upload

Standard GPX format dari GPS device atau aplikasi tracking.

### 5. Manual Input

Input koordinat secara manual untuk lokasi statis.

---

## 📤 Export Data

### CSV Format

```csv
session_id,timestamp,damage_type,confidence,latitude,longitude,severity,address
SESSION001,2026-01-08 10:00:00,Pothole,0.87,-6.9024,107.6188,high,"Jl. Example"
```

### GeoJSON Format

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [107.6188, -6.9024]
      },
      "properties": {
        "damage_type": "Pothole",
        "confidence": 0.87,
        "severity": "high"
      }
    }
  ]
}
```

### KML Format

Compatible dengan Google Earth dan aplikasi mapping lainnya.

---

## 🎯 Tracking System

### ByteTrack Algorithm

RoadGuard menggunakan ByteTrack untuk tracking objek dengan fitur:

1. **IoU-based Matching**
   - Menghubungkan deteksi antar frame berdasarkan Intersection over Union
   - Threshold dapat dikonfigurasi (default: 0.3)

2. **Spatial Filtering**
   - Menghindari duplikasi deteksi pada lokasi yang sama
   - Menggunakan Haversine distance untuk GPS

3. **Track Lifecycle**
   - **Active**: Track yang sedang dimonitor
   - **Lost**: Track yang hilang sementara
   - **Confirmed**: Track yang valid setelah minimum hits

### Anti-Duplicate Logic

```python
# Cek jarak GPS
distance = haversine(lat1, lon1, lat2, lon2)
if distance < MIN_DISTANCE:
    # Skip duplicate
    continue
```

---

## 🗄 Database

### Schema

#### Table: sessions

```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    start_time TEXT,
    end_time TEXT,
    video_source TEXT,
    gps_mode TEXT,
    total_detections INTEGER,
    total_frames INTEGER
);
```

#### Table: detections

```sql
CREATE TABLE detections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    timestamp TEXT,
    frame_number INTEGER,
    damage_type TEXT,
    confidence REAL,
    bbox TEXT,  -- JSON format
    latitude REAL,
    longitude REAL,
    severity TEXT,
    track_id INTEGER,
    evidence_path TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);
```

### Query Examples

```python
# Get all detections from a session
detections = db.get_session_detections("SESSION001")

# Get high severity detections
high_severity = db.query(
    "SELECT * FROM detections WHERE severity='high'"
)

# Statistics by damage type
stats = db.query("""
    SELECT damage_type, COUNT(*) as count 
    FROM detections 
    GROUP BY damage_type
""")
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. **Model Not Found**

**Error:** `FileNotFoundError: model file not found`

**Solution:**
- Pastikan file model ada di `src/models/`
- Check path di konfigurasi

#### 2. **Camera Access Denied**

**Error:** `Cannot access webcam`

**Solution:**
- Pastikan webcam tidak digunakan aplikasi lain
- Cek permission browser/OS
- Restart aplikasi

#### 3. **GPS Not Working**

**Error:** `Cannot get GPS location`

**Solution:**
- Untuk Realtime: Enable GPS & izinkan browser access
- Cek koneksi internet (untuk geocoding)
- Gunakan simulation mode untuk testing

#### 4. **Slow Detection**

**Problem:** FPS rendah saat deteksi

**Solution:**
- Gunakan model yang lebih kecil (yolov8n)
- Kurangi resolusi video
- Skip frames (process every N frames)
- Gunakan GPU jika tersedia

#### 5. **Import Error**

**Error:** `ModuleNotFoundError`

**Solution:**
```bash
pip install -r requirements.txt --upgrade
```

### Performance Tips

1. **GPU Acceleration**
```bash
# Install CUDA version
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

2. **Frame Skipping**
```python
# Process every 3rd frame
if frame_count % 3 == 0:
    detections = detector.detect(frame)
```

3. **Model Optimization**
- Gunakan model yang lebih kecil untuk real-time
- Export ke ONNX untuk inference lebih cepat

---

## 🤝 Kontribusi

Kontribusi sangat diterima! Berikut cara berkontribusi:

### Steps to Contribute

1. Fork repository
2. Create feature branch
   ```bash
   git checkout -b feature/AmazingFeature
   ```
3. Commit changes
   ```bash
   git commit -m 'Add some AmazingFeature'
   ```
4. Push to branch
   ```bash
   git push origin feature/AmazingFeature
   ```
5. Open Pull Request

### Contribution Guidelines

- Follow PEP 8 style guide
- Add docstrings untuk fungsi baru
- Test code sebelum submit
- Update documentation jika diperlukan

---

## 📝 Lisensi

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👥 Tim Pengembang

- **Developer**: [Your Name]
- **Contact**: [Your Email]
- **GitHub**: [Your GitHub Profile]

---

## 🙏 Acknowledgments

- **Ultralytics YOLOv8**: Object detection framework
- **Streamlit**: Web application framework
- **RDD Dataset**: Road Damage Detection dataset
- **ByteTrack**: Multi-object tracking algorithm
- **OpenCV**: Computer vision library

---

## 📚 Referensi

1. [YOLOv8 Documentation](https://docs.ultralytics.com/)
2. [Streamlit Documentation](https://docs.streamlit.io/)
3. [RDD2022 Dataset](https://github.com/sekilab/RoadDamageDetector)
4. [ByteTrack Paper](https://arxiv.org/abs/2110.06864)

---

## 📞 Support

Jika Anda mengalami masalah atau memiliki pertanyaan:

- 📧 Email: your.email@example.com
- 🐛 Issues: [GitHub Issues](https://github.com/yourusername/roadguard-vision/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/yourusername/roadguard-vision/discussions)

---

## 🔮 Future Roadmap

- [ ] Support untuk model detection tambahan
- [ ] Mobile app (Android/iOS)
- [ ] Cloud deployment (AWS/Azure/GCP)
- [ ] Real-time collaboration features
- [ ] Advanced analytics dashboard
- [ ] API endpoints untuk integrasi
- [ ] Automated report generation
- [ ] Machine learning model retraining interface

---

<div align="center">

**Made with ❤️ for better road infrastructure**

⭐ Star repository ini jika bermanfaat!

[Report Bug](https://github.com/yourusername/roadguard-vision/issues) • [Request Feature](https://github.com/yourusername/roadguard-vision/issues)

</div>
