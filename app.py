import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from groq import Groq
import re

# --- 1. SAYFA AYARLARI ---
st.set_page_config(
    page_title="ODAK | Vision",
    page_icon="🍎",
    layout="wide"
)

# --- 2. GURU CSS: APPLE STYLE ANIMATIONS & LAYOUT ---
st.markdown("""
    <style>
    /* 1. GENEL TYPOGRAPHY VE ARKA PLAN */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    
    .stApp {
        background-color: #FBFBFD; /* Apple'ın meşhur kırık beyazı */
        font-family: 'Inter', sans-serif;
        color: #1D1D1F;
    }
    
    /* 2. ANİMASYON TANIMLARI (KEYFRAMES) */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translate3d(0, 40px, 0); }
        to { opacity: 1; transform: translate3d(0, 0, 0); }
    }

    /* Animasyon Sınıfları (Gecikmeli) */
    .reveal-1 { animation: fadeInUp 0.8s ease-out forwards; opacity: 0; }
    .reveal-2 { animation: fadeInUp 0.8s ease-out 0.3s forwards; opacity: 0; }
    .reveal-3 { animation: fadeInUp 0.8s ease-out 0.6s forwards; opacity: 0; }
    .reveal-4 { animation: fadeInUp 0.8s ease-out 0.9s forwards; opacity: 0; }

    /* 3. HERO SECTION (ŞİRKET KARTI) */
    .hero-container {
        padding: 40px 0;
        text-align: center;
        margin-bottom: 40px;
    }
    .company-title {
        font-size: 56px;
        font-weight: 600;
        letter-spacing: -1px;
        color: #1D1D1F;
        margin-bottom: 10px;
    }
    .company-sector {
        font-size: 20px;
        color: #86868B;
        font-weight: 300;
    }
    .company-desc {
        font-size: 16px;
        color: #424245;
        max-width: 800px;
        margin: 20px auto;
        line-height: 1.6;
    }

    /* 4. METRİK KARTLARI (GLASS EFFECT) */
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.8);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(0,0,0,0.05);
        border-radius: 18px;
        padding: 20px;
        box-shadow: 0 4px 24px rgba(0,0,0,0.04);
        transition: transform 0.3s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 30px rgba(0,0,0,0.08);
    }
    div[data-testid="stMetric"] label { color: #86868B !important; font-size: 14px; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #1D1D1F !important; font-size: 28px; font-weight: 600; }

    /* 5. F-RAY PUAN KUTUSU (PREMIUM) */
    .score-container {
        text-align: center;
        background: linear-gradient(135deg, #000000 0%, #1a1a1a 100%);
        color: white;
        padding: 30px;
        border-radius: 24px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.2);
    }

    /* 6. AI KUTUSU (MINIMAL) */
    .ai-box {
        background-color: #FFFFFF;
        border-radius: 18px;
        padding: 40px;
        box-shadow: 0 4px 24px rgba(0,0,0,0.04);
        border: 1px solid rgba(0,0,0,0.05);
        font-size: 17px;
        line-height: 1.7;
        color: #333;
    }
    
    /* Gerekli Streamlit Ayarlarını Temizle */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
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

# --- 5. FONKSİYONLAR ---
def rsi_hesapla(data, window=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def veri_getir(sembol):
    try:
        hisse = yf.Ticker(sembol)
        bilgi = hisse.info
        fast_info = hisse.fast_info
        
        guncel_fiyat = bilgi.get('currentPrice')
        if guncel_fiyat is None: guncel_fiyat = fast_info.last_price
        if guncel_fiyat is None: return None

        def guvenli_al(anahtar, varsayilan=0):
            deger = bilgi.get(anahtar)
            return varsayilan if deger is None else deger

        fk = guvenli_al('trailingPE', 0)
        if fk == 0:
            eps = guvenli_al('trailingEps', 0)
            if eps != 0: fk = guncel_fiyat / eps

        pd_dd = guvenli_al('priceToBook', 0)
        roe = guvenli_al('returnOnEquity', 0) * 100
        buyume = guvenli_al('revenueGrowth', 0) * 100
        
        hist = hisse.history(period="1y")
        hist['RSI'] = rsi_hesapla(hist)
        son_rsi = hist['RSI'].iloc[-1]
        
        onceki_kapanis = hist['Close'].iloc[-2]
        degisim = ((guncel_fiyat - onceki_kapanis) / onceki_kapanis) * 100

        # F-RAY Puanı
        puan = 0
        if roe > 30: puan += 30
        elif roe > 10: puan += 15
        if 0 < fk < 10: puan += 30
        elif 10 <= fk < 20: puan += 15
        if 30 <= son_rsi <= 70: puan += 20
        if buyume > 20: puan += 20
        
        # İngilizce Özeti çekiyoruz (AI çevirecek)
        ozet = bilgi.get('longBusinessSummary', 'Şirket açıklaması bulunamadı.')
        sektor = bilgi.get('sector', 'Bilinmiyor')
        
        return {
            'ad': bilgi.get('longName', sembol),
            'fiyat': guncel_fiyat, 'fk': fk, 'pd_dd': pd_dd,
            'roe': roe, 'buyume': buyume, 'rsi': son_rsi,
            'degisim': degisim, 'puan': min(puan, 100),
            'hist': hist, 'ozet': ozet, 'sektor': sektor
        }
    except Exception as e: return None

def metni_temizle(metin):
    metin = re.sub(r'[^\x00-\x7F\u00C0-\u00FF\u0100-\u017F\s.,;:!?()"\'-]', '', metin)
    yasakli = ["approximately", "slightly", "doing", "trading", "However", "overall"]
    for k in yasakli: metin = metin.replace(k, "").replace(k.lower(), "")
    return metin

@st.cache_data(ttl=0, show_spinner=False)
def ai_analiz(veri):
    try:
        prompt = f"""
        GÖREV: {veri['ad']} hissesini analiz et.
        
        1. KISIM: Şirketin İngilizce özetini ({veri['ozet'][:200]}...) temel alarak şirketin ne iş yaptığını 2 cümleyle Türkçe anlat.
        2. KISIM: Verileri yorumla (Fiyat: {veri['fiyat']}, F/K: {veri['fk']:.2f}, ROE: %{veri['roe']:.1f}, Puan: {veri['puan']}/100).
        
        KURALLAR:
        - Başlık kullanma, direkt paragrafla başla.
        - Çok akıcı, hikaye anlatır gibi, Apple lansmanı tadında Türkçe konuş.
        - Yabancı karakter kullanma.
        """
        chat = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.1
        )
        return metni_temizle(chat.choices[0].message.content)
    except Exception as e: return f"AI Hatası: {str(e)}"

# --- 6. ARAYÜZ ---
# Sidebar (Gizli gibi duran minimal sidebar)
st.sidebar.markdown("###  ODAK")
list_secenekler = [f"{k} - {v}" for k, v in BIST_SIRKETLERI.items()]
secim1 = st.sidebar.selectbox("Hisse Seçiniz", list_secenekler, index=0)
kod1 = secim1.split(" - ")[0] + ".IS"
analyze_btn = st.sidebar.button("Analiz Et")

if analyze_btn:
    with st.spinner('Veriler işleniyor...'):
        data = veri_getir(kod1)
        if not data: st.error("Veri alınamadı."); st.stop()
        
        # --- BÖLÜM 1: HERO SECTION (Gecikme Yok) ---
        # Burası direkt yüklenir, şirketin ihtişamını gösterir.
        st.markdown(f"""
        <div class='hero-container reveal-1'>
            <div class='company-sector'>{data['sektor']}</div>
            <div class='company-title'>{data['ad']}</div>
            <div class='company-desc'>Hisse Fiyatı: <b>{data['fiyat']:.2f} ₺</b> <span style='color: {'#2ecc71' if data['degisim']>0 else '#e74c3c'}'>%{data['degisim']:.2f}</span></div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")

        # --- BÖLÜM 2: KARNELER VE METRİKLER (Gecikmeli Gelir) ---
        c_score, c_metrics = st.columns([1, 2])
        
        with c_score:
            renk = "#2ecc71" if data['puan'] >= 80 else ("#f1c40f" if data['puan'] >= 50 else "#e74c3c")
            st.markdown(f"""
            <div class='reveal-2'>
                <div class='score-container'>
                    <div style='font-size: 14px; opacity: 0.7; letter-spacing: 2px;'>F-RAY PUANI</div>
                    <div style='font-size: 64px; font-weight: 700; margin: 10px 0;'>{data['puan']}</div>
                    <div style='color: {renk}; font-weight: 600;'>{'MÜKEMMEL' if data['puan']>=80 else 'İYİ / ORTA'}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with c_metrics:
            st.markdown("<div class='reveal-2'>", unsafe_allow_html=True)
            m1, m2 = st.columns(2)
            m1.metric("F/K Oranı", f"{data['fk']:.2f}")
            m1.metric("ROE (Karlılık)", f"%{data['roe']:.1f}")
            m2.metric("Büyüme", f"%{data['buyume']:.1f}")
            m2.metric("RSI", f"{data['rsi']:.1f}")
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<br><br>", unsafe_allow_html=True)

        # --- BÖLÜM 3: GRAFİK (Daha Geç Gelir) ---
        st.markdown("<div class='reveal-3'>", unsafe_allow_html=True)
        st.markdown("### 📉 Piyasa Hareketi")
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=data['hist'].index, open=data['hist']['Open'], 
                                     high=data['hist']['High'], low=data['hist']['Low'], 
                                     close=data['hist']['Close'], name=data['ad']))
        fig.update_layout(height=400, template="plotly_white", margin=dict(t=20, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<br><br>", unsafe_allow_html=True)

        # --- BÖLÜM 4: AI STORYTELLING (En Son Gelir) ---
        st.markdown("<div class='reveal-4'>", unsafe_allow_html=True)
        st.markdown("### 🧠 ODAK Görüşü")
        yorum = ai_analiz(data)
        st.markdown(f"<div class='ai-box'>{yorum}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

else:
    # Boş ekranda şık bir karşılama
    st.markdown("""
    <div style='text-align: center; padding-top: 100px;'>
        <h1 style='color: #1D1D1F; font-size: 48px;'>Yatırımın Geleceği.</h1>
        <p style='color: #86868B; font-size: 20px;'>Analiz etmek için sol menüden bir hisse seçin.</p>
    </div>
    """, unsafe_allow_html=True)
