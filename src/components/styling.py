import streamlit as st

# 1. KOLEKSI ICON SVG (Gaya Lucide/Modern)
ICONS = {
    "dashboard": """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/></svg>""",
    "map": """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.106 5.553a2 2 0 0 0 1.788 0l3.659-1.83A1 1 0 0 1 21 4.619v12.764a1 1 0 0 1-.553.894l-4.553 2.277a2 2 0 0 1-1.788 0l-4.212-2.106a2 2 0 0 0-1.788 0l-3.659 1.83A1 1 0 0 1 3 19.381V6.618a1 1 0 0 1 .553-.894l4.553-2.277a2 2 0 0 1 1.788 0z"/></svg>""",
    "alert": """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FF4B4B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>""",
    "video": """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m22 8-6 4 6 4V8Z"/><rect width="14" height="12" x="2" y="6" rx="2" ry="2"/></svg>""",
    "settings": """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.1a2 2 0 0 1-1-1.72v-.51a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>"""
}

# 2. LOAD CSS (GLASSMORPHISM)
def load_css():
    st.markdown("""
        <style>
        /* Background Gelap Elegan */
        .stApp {
            background: linear-gradient(to bottom right, #0f2027, #203a43, #2c5364); 
            color: #e0e0e0;
        }
        
        /* Card Glassmorphism */
        .glass-card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 15px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        /* HANYA SEMBUNYIKAN MENU & FOOTER, JANGAN HEADER */
        #MainMenu {visibility: hidden;} 
        footer {visibility: hidden;}
        
        /* Jika ingin header transparan tapi tombol sidebar tetap ada: */
        header[data-testid="stHeader"] {
            background-color: transparent;
        }
        
        /* Opsional: Sembunyikan garis pelangi di atas jika mengganggu */
        .stApp > header {
            background-color: transparent;
        }

        /* ... (Styling Judul & Metrik tetap sama) ... */
        .header-title {
            font-family: 'Helvetica Neue', sans-serif;
            font-weight: 700;
            font-size: 1.8rem;
            background: -webkit-linear-gradient(#00e5ff, #0072ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0px;
        }
        
        .header-subtitle {
            font-size: 0.9rem;
            color: #a0a0a0;
            margin-bottom: 20px;
        }

        div[data-testid="stMetricValue"] {
            font-size: 24px;
            color: #00e5ff;
            text-shadow: 0 0 10px rgba(0, 229, 255, 0.3);
        }
        </style>
        """, unsafe_allow_html=True)

# 3. HELPER FUNCTION UNTUK HEADER DENGAN ICON
def render_icon_header(icon_name, text):
    svg = ICONS.get(icon_name, "")
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 10px;">
        {svg}
        <span style="font-size: 1.1rem; font-weight: 600;">{text}</span>
    </div>
    """, unsafe_allow_html=True)