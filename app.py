import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from groq import Groq
import re

# --- 1. SAYFA AYARLARI ---
st.set_page_config(
    page_title="ODAK | Master",
    page_icon="🎯",
    layout="wide"
)

# --- 2. CSS SİHİRBAZLIĞI (KARARLI SÜRÜM) ---
st.markdown("""
    <style>
    /* GENEL FONT */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    .stApp {
        background-color: #F8F9FA; /* Yumuşak Beyaz */
        color: #111111; /* Kömür Siyahı */
        font-family: 'Inter', sans-serif;
    }

    /* --- SIDEBAR TASARIMI (BORDO & BEYAZ) --- */
    /* Sidebar Arka Planı */
    section[data-testid="stSidebar"] {
        background-color: #8B0000 !important; /* Koyu Bordo */
    }
    
    /* Sidebar içindeki TÜM yazılar */
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3, 
    section[data-testid="stSidebar"] label, 
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] div,
    section[data-testid="stSidebar"] span {
        color: #FFFFFF !important; /* Zorla Beyaz Yap */
    }

    /* Selectbox (Açılır Menü) İyileştirme */
    div[data-testid="stSidebar"] div[data-baseweb="select"] > div {
        background-color: rgba(255, 255, 255, 0.2) !important;
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
    }
    /* Selectbox içindeki ikonlar */
    div[data-testid="stSidebar"] svg {
        fill: white !important;
    }

    /* Buton Tasarımı */
    div[data-testid="stSidebar"] .stButton > button {
        background-color: #FFFFFF !important;
        color: #8B0000 !important;
        font-weight: bold;
        border: none;
        width: 100%;
        padding: 12px;
        border-radius: 8px;
        transition: all 0.3s;
    }
    div[data-testid="stSidebar"] .stButton > button:hover {
        background-color: #f1f1f1 !important;
        transform: scale(1.02);
    }

    /* --- KART TASARIMLARI (MAIN PAGE) --- */
    
    /* Hero Section (Başlık) */
    .hero-box {
        text-align: center;
        padding: 40px 20px;
        margin-bottom: 30px;
    }
    .company-name { font-size: 42px; font-weight: 800; color: #111; margin: 0; }
    .company-meta { font-size: 18px; color: #666; margin-top: 5px; }
    .price-tag { 
        font-size: 36px; font-weight: 700; color: #111; 
        background: #fff; padding: 10px 25px; border-radius: 50px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        display: inline-block; margin-top: 15px;
    }

    /* Metrik Kutuları */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E0E0E0 !important;
        border-radius: 12px !important;
        padding: 15px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05) !important;
    }
    div[data-testid="stMetric"] label { color: #666 !important; font-size: 14px !important; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #111 !important; font-size: 24px !important; }

    /* Puan Kutusu */
    .score-card {
        background: #111;
        color: #fff;
        padding: 30px;
        border-radius: 16px;
        text-align: center;
        box-shadow: 0 10px 30px rgba(0,0,0,0.15);
    }
    
    /* AI Kutusu */
    .ai-card {
        background: #fff;
        border-left: 5px solid #111;
        padding: 25px;
        border-radius: 8px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.04);
        line-height: 1.6;
        color: #333;
    }

    </style>
    """, unsafe_allow_html=True)

# --- 3. SABİT LİSTE ---
BIST_SIRKETLERI = {
    "THYAO": "TÜRK HAVA YOLLARI", "GARAN": "GARANTİ BBVA", "ASELS": "ASELSAN",
    "EREGL": "EREĞLİ DEMİR ÇELİK", "TUPRS": "TÜPRAŞ", "SISE": "ŞİŞECAM",
    "AKBNK": "AKBANK", "YKBNK": "YAPI KREDİ", "ISCTR": "İŞ BANKASI (C)",
    "KCHOL": "KOÇ HOLDİNG", "SAHOL": "SABANCI HOLDİNG", "BIMAS": "BİM MAĞAZALAR",
    "FROTO": "FORD OTOSAN", "TOASO": "TOFAŞ OTO", "PGSUS": "PEGASUS",
    "TCELL": "TURKCELL", "TTKOM": "TÜRK TELEKOM", "PETKM": "PETKİM",
    "SASA": "SASA POLYESTER", "HEKTS": "HEKTAŞ", "ENKAI": "ENKA İNŞAAT",
    "VESTL": "VESTEL", "ARCLK": "ARÇELİK", "KONTR": "KONTROLMATİK",
    "ASTOR": "ASTOR ENERJİ", "KOZAL": "KOZA ALTIN", "ODAS": "ODAŞ ELEKTRİK",
    "EKGYO": "EMLAK KONUT", "MGROS": "MİGROS", "DOAS": "DOĞUŞ OTOMOTİV"
}

# --- 4. API ---
try:
    api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=api_key)
except: st.error("API Key Hatası"); st.stop()

# --- 5. KARARLI VERİ MOTORU ---
def rsi_hesapla(data, window=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def veri_getir(sembol):
    try:
        hisse = yf.Ticker(sembol)
        
        # 1. Önce Geçmiş Veriyi Al (En Garanti Yöntem)
        hist = hisse.history(period="1y")
        
        if hist.empty:
            return None # Grafik yoksa iptal

        # Fiyatı geçmiş veriden al (Yahoo bazen info'da vermez)
        guncel_fiyat = hist['Close'].iloc[-1]
        
        # 2. Temel Bilgileri Almaya Çalış
        try:
            bilgi = hisse.info
        except:
            bilgi = {} # Hata verirse boş sözlük yap, çökmesin

        # Veri Yoksa '0' Döndür (Çökme Engelleyici)
        def guvenli(key):
            val = bilgi.get(key)
            return val if val is not None else 0

        fk = guvenli('trailingPE')
        pd_dd = guvenli('priceToBook')
        roe = guvenli('returnOnEquity') * 100
        buyume = guvenli('revenueGrowth') * 100
        ad = bilgi.get('longName', sembol)
        sektor = bilgi.get('sector', 'BIST Şirketi')
        ozet = bilgi.get('longBusinessSummary', 'Özet bulunamadı.')

        # F/K 0 geldiyse hesaplamayı dene
        if fk == 0:
            eps = guvenli('trailingEps')
            if eps != 0: fk = guncel_fiyat / eps

        # 3. Teknik
        hist['RSI'] = rsi_hesapla(hist)
        son_rsi = hist['RSI'].iloc[-1]
        onceki_kapanis = hist['Close'].iloc[-2]
        degisim = ((guncel_fiyat - onceki_kapanis) / onceki_kapanis) * 100

        # 4. Puanlama
        puan = 0
        if roe > 30: puan += 30
        elif roe > 10: puan += 15
        if 0 < fk < 15: puan += 30
        elif 15 <= fk < 25: puan += 15
        if 30 <= son_rsi <= 70: puan += 20
        if buyume > 20: puan += 20
        
        return {
            'ad': ad, 'sektor': sektor, 'ozet': ozet,
            'fiyat': guncel_fiyat, 'degisim': degisim,
            'fk': fk, 'pd_dd': pd_dd, 'roe': roe, 'buyume': buyume,
            'rsi': son_rsi, 'puan': min(puan, 100), 'hist': hist
        }

    except Exception as e:
        print(f"Hata: {e}")
        return None

def metni_temizle(metin):
    metin = re.sub(r'[^\x00-\x7F\u00C0-\u00FF\u0100-\u017F\s.,;:!?()"\'-]', '', metin)
    yasakli = ["approximately", "slightly", "doing", "trading", "However", "overall"]
    for k in yasakli: metin = metin.replace(k, "").replace(k.lower(), "")
    return metin

@st.cache_data(ttl=3600, show_spinner=False)
def ai_analiz(veri):
    try:
        prompt = f"""
        Rol: Finansal Mentor. Dil: Türkçe.
        Hisse: {veri['ad']}
        Veriler: Fiyat {veri['fiyat']:.2f}, F/K {veri['fk']:.2f}, ROE %{veri['roe']:.1f}, Puan {veri['puan']}/100.
        Görev: Bu verileri yorumla. Şirket ne iş yapar kısaca bahset. Yatırımcıya risk ve fırsatları anlat.
        """
        chat = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.1
        )
        return metni_temizle(chat.choices[0].message.content)
    except: return "AI servisi şu an meşgul. Lütfen grafik ve metrikleri inceleyin."

# --- 6. ARAYÜZ ---

# Sidebar
st.sidebar.markdown("### 🎯 ODAK")
secim1 = st.sidebar.selectbox("Hisse Seçiniz", [f"{k} - {v}" for k, v in BIST_SIRKETLERI.items()])
kod1 = secim1.split(" - ")[0] + ".IS"
analyze_btn = st.sidebar.button("ANALİZ ET")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📚 AKADEMİ")
with st.sidebar.expander("Terimler Sözlüğü"):
    st.markdown("""
    * **F/K:** Şirketin kendini amorti süresi. (Düşük iyidir).
    * **ROE:** Sermaye verimliliği. (Yüksek iyidir).
    * **RSI:** Alım/Satım iştahı. (30 ucuz, 70 pahalı).
    """)
st.sidebar.info("⚠️ Veriler bilgi amaçlıdır. Yatırım tavsiyesi değildir.")

# Ana Sayfa
if analyze_btn:
    with st.spinner('Piyasa taranıyor...'):
        data = veri_getir(kod1)
        
        if data:
            # 1. HERO BÖLÜMÜ
            st.markdown(f"""
            <div class='hero-box'>
                <div style='color:#888; letter-spacing:2px; font-size:14px; text-transform:uppercase;'>{data['sektor']}</div>
                <h1 class='company-name'>{data['ad']}</h1>
                <div class='price-tag'>
                    {data['fiyat']:.2f} ₺ 
                    <span style='color:{'#27ae60' if data['degisim']>0 else '#c0392b'}; font-size:20px; vertical-align:middle;'>
                        %{data['degisim']:.2f}
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # 2. PUAN VE METRİKLER (YAN YANA)
            c1, c2 = st.columns([1, 2])
            
            with c1:
                # Puan Kartı
                puan_renk = "#27ae60" if data['puan'] >= 80 else ("#f1c40f" if data['puan'] >= 50 else "#e74c3c")
                durum = "MÜKEMMEL" if data['puan'] >= 80 else ("İYİ / ORTA" if data['puan'] >= 50 else "RİSKLİ")
                
                st.markdown(f"""
                <div class='score-card'>
                    <div style='font-size:12px; opacity:0.7; margin-bottom:10px;'>SAĞLIK PUANI</div>
                    <div style='font-size:64px; font-weight:800; line-height:1;'>{data['puan']}</div>
                    <div style='color:{puan_renk}; margin-top:10px; font-weight:bold;'>{durum}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with c2:
                # Metrikler Grid
                m1, m2 = st.columns(2)
                # Veri varsa göster, yoksa '-' koy
                fk_txt = f"{data['fk']:.2f}" if data['fk'] > 0 else "-"
                roe_txt = f"%{data['roe']:.1f}" if data['roe'] != 0 else "-"
                buyume_txt = f"%{data['buyume']:.1f}" if data['buyume'] != 0 else "-"
                
                m1.metric("F/K Oranı", fk_txt)
                m1.metric("ROE (Karlılık)", roe_txt)
                m2.metric("Büyüme", buyume_txt)
                m2.metric("RSI (Teknik)", f"{data['rsi']:.1f}")
            
            st.markdown("---")
            
            # 3. GRAFİK VE AI (ALT ALTA)
            st.markdown("### 📉 Teknik Görünüm")
            fig = go.Figure(data=[go.Candlestick(x=data['hist'].index, open=data['hist']['Open'], 
                            high=data['hist']['High'], low=data['hist']['Low'], close=data['hist']['Close'])])
            fig.update_layout(height=400, template="plotly_white", margin=dict(t=0,b=0,l=0,r=0))
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("### 🧠 ODAK Görüşü")
            yorum = ai_analiz(data)
            st.markdown(f"<div class='ai-card'>{yorum}</div>", unsafe_allow_html=True)

        else:
            st.error("Veri çekilemedi. Lütfen tekrar deneyin veya başka bir hisse seçin.")

else:
    # Karşılama Ekranı
    st.markdown("""
    <div style='text-align:center; padding-top:100px;'>
        <h1 style='color:#111;'>Yatırımın Odak Noktası.</h1>
        <p style='color:#666;'>Analize başlamak için sol menüyü kullanın.</p>
    </div>
    """, unsafe_allow_html=True)
