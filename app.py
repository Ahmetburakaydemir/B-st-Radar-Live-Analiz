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

# --- 2. GURU CSS: APPLE STYLE + RED SIDEBAR ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    .stApp {
        background-color: #FBFBFD;
        font-family: 'Inter', sans-serif;
        color: #1D1D1F;
    }

    /* --- SIDEBAR TASARIMI (BORDO) --- */
    section[data-testid="stSidebar"] {
        background-color: #8B0000;
    }
    section[data-testid="stSidebar"] * {
        color: #FFFFFF !important;
    }
    div[data-testid="stSidebar"] .stSelectbox > div > div {
        background-color: rgba(255,255,255,0.1);
        color: white;
        border: 1px solid rgba(255,255,255,0.2);
    }
    div[data-testid="stSidebar"] .stButton > button {
        background-color: #FFFFFF;
        color: #8B0000;
        font-weight: bold;
        border: none;
        width: 100%;
    }

    /* --- ANİMASYONLAR --- */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translate3d(0, 40px, 0); }
        to { opacity: 1; transform: translate3d(0, 0, 0); }
    }
    .reveal-1 { animation: fadeInUp 0.8s ease-out forwards; opacity: 0; }
    .reveal-2 { animation: fadeInUp 0.8s ease-out 0.3s forwards; opacity: 0; }
    .reveal-3 { animation: fadeInUp 0.8s ease-out 0.6s forwards; opacity: 0; }
    .reveal-4 { animation: fadeInUp 0.8s ease-out 0.9s forwards; opacity: 0; }

    /* --- KART TASARIMLARI --- */
    .hero-container { padding: 30px 0; text-align: center; margin-bottom: 20px; }
    .company-title { font-size: 48px; font-weight: 700; color: #1D1D1F; letter-spacing: -1px; }
    .company-sector { font-size: 16px; color: #86868B; text-transform: uppercase; letter-spacing: 1px; }
    
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.9);
        border: 1px solid rgba(0,0,0,0.08);
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.03);
    }

    .score-container {
        text-align: center;
        background: #1D1D1F;
        color: white;
        padding: 20px;
        border-radius: 16px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.15);
    }
    
    .ai-box {
        background-color: #FFFFFF;
        border-radius: 12px;
        padding: 25px;
        border: 1px solid rgba(0,0,0,0.05);
        box-shadow: 0 4px 15px rgba(0,0,0,0.03);
        line-height: 1.7;
        color: #333;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. LİSTE ---
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

# --- 5. ZIRHLI VERİ MOTORU ---
def rsi_hesapla(data, window=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def veri_getir(sembol):
    """
    Bu fonksiyon asla 'None' dönüp sistemi çökertmemeye çalışır.
    Fiyat bulursa devam eder, detaylar yoksa '0' atar.
    """
    try:
        hisse = yf.Ticker(sembol)
        
        # 1. ADIM: GRAFİK VE FİYAT (EN ÖNEMLİSİ)
        # 1 yıllık veri çekmeyi dene
        hist = hisse.history(period="1y")
        
        if hist.empty:
            return None # Grafik bile yoksa yapacak bir şey yok
            
        # Son kapanış fiyatını geçmiş veriden al (En garantisi budur)
        guncel_fiyat = hist['Close'].iloc[-1]
        
        # 2. ADIM: TEMEL BİLGİLER (INFO)
        # Burası hata verirse varsayılan değerlerle devam et
        try:
            bilgi = hisse.info
        except:
            bilgi = {} # Boş sözlük

        # Güvenli Veri Çekme
        def guvenli_al(anahtar, varsayilan=0):
            val = bilgi.get(anahtar)
            return varsayilan if val is None else val

        fk = guvenli_al('trailingPE', 0)
        pd_dd = guvenli_al('priceToBook', 0)
        roe = guvenli_al('returnOnEquity', 0) * 100
        buyume = guvenli_al('revenueGrowth', 0) * 100
        ad = bilgi.get('longName', sembol)
        sektor = bilgi.get('sector', 'BIST Şirketi')
        ozet = bilgi.get('longBusinessSummary', 'Şirket açıklaması çekilemedi.')

        # 3. ADIM: TEKNİK HESAPLAMA
        hist['RSI'] = rsi_hesapla(hist)
        son_rsi = hist['RSI'].iloc[-1]
        onceki_kapanis = hist['Close'].iloc[-2]
        degisim = ((guncel_fiyat - onceki_kapanis) / onceki_kapanis) * 100

        # 4. ADIM: PUANLAMA
        puan = 0
        # Puanlama kriterleri (Basitleştirilmiş)
        if roe > 30: puan += 30
        elif roe > 10: puan += 15
        if 0 < fk < 12: puan += 30
        elif 12 <= fk < 20: puan += 15
        if 30 <= son_rsi <= 70: puan += 20
        if buyume > 20: puan += 20
        
        return {
            'ad': ad,
            'fiyat': guncel_fiyat, 'fk': fk, 'pd_dd': pd_dd,
            'roe': roe, 'buyume': buyume, 'rsi': son_rsi,
            'degisim': degisim, 'puan': min(puan, 100),
            'hist': hist, 'ozet': ozet, 'sektor': sektor
        }
        
    except Exception as e:
        # Eğer çok kritik bir hata olursa (örn: internet yoksa)
        print(f"Kritik Hata: {e}")
        return None

def metni_temizle(metin):
    metin = re.sub(r'[^\x00-\x7F\u00C0-\u00FF\u0100-\u017F\s.,;:!?()"\'-]', '', metin)
    yasakli = ["approximately", "slightly", "doing", "trading", "However", "overall"]
    for k in yasakli: metin = metin.replace(k, "").replace(k.lower(), "")
    return metin

@st.cache_data(ttl=3600, show_spinner=False) # Cache süresini artırdık
def ai_analiz(veri):
    try:
        prompt = f"""
        GÖREV: {veri['ad']} hissesini analiz et.
        VERİLER: Fiyat: {veri['fiyat']:.2f}, F/K: {veri['fk']:.2f}, ROE: %{veri['roe']:.1f}, Puan: {veri['puan']}/100.
        ÖZET: {veri['ozet'][:150]}...
        
        1. KISIM: Şirket ne iş yapar? (1 Cümle)
        2. KISIM: Bu finansal veriler ne anlatıyor?
        KURALLAR: Türkçe konuş. Akıcı ol.
        """
        chat = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.1
        )
        return metni_temizle(chat.choices[0].message.content)
    except Exception as e: return f"AI Hatası: {str(e)}"

# --- 6. ARAYÜZ ---
st.sidebar.markdown("### 🎯 ODAK")
secim1 = st.sidebar.selectbox("Hisse Seçiniz", [f"{k} - {v}" for k, v in BIST_SIRKETLERI.items()])
kod1 = secim1.split(" - ")[0] + ".IS"
analyze_btn = st.sidebar.button("ANALİZ ET")

# ODAK AKADEMİ (Sözlük)
st.sidebar.markdown("---")
st.sidebar.markdown("### 📚 ODAK AKADEMİ")
with st.sidebar.expander("📝 Finansal Terimler"):
    st.markdown("""
    **💰 F/K (Fiyat/Kazanç):** Paranızı kaç yılda amorti edersiniz? (0-10 arası ucuzdur).
    **🚀 ROE (Özsermaye Karlılığı):** Şirket parayı ne kadar iyi yönetiyor? (%30 üstü harika).
    **📊 RSI:** 30 altı ucuz, 70 üstü pahalı sinyalidir.
    """)
st.sidebar.info("⚠️ **Yasal Uyarı:** Veriler ve AI yorumları hata içerebilir. Yatırım tavsiyesi değildir.")

if analyze_btn:
    with st.spinner('ODAK motoru piyasayı tarıyor...'):
        data = veri_getir(kod1)
        if not data: 
            st.error("Veri alınamadı. (Yahoo Finance geçici olarak yanıt vermiyor olabilir, lütfen tekrar deneyin).")
            st.stop()
        
        # 1. HERO
        st.markdown(f"""
        <div class='hero-container reveal-1'>
            <div class='company-sector'>{data['sektor']}</div>
            <div class='company-title'>{data['ad']}</div>
            <div class='company-desc'>
                Fiyat: <b>{data['fiyat']:.2f} ₺</b> 
                <span style='color: {'#2ecc71' if data['degisim']>0 else '#e74c3c'};'>%{data['degisim']:.2f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")

        # 2. METRİKLER
        c_score, c_metrics = st.columns([1, 2])
        with c_score:
            renk = "#2ecc71" if data['puan'] >= 80 else ("#f1c40f" if data['puan'] >= 50 else "#e74c3c")
            st.markdown(f"""
            <div class='reveal-2'>
                <div class='score-container'>
                    <div style='font-size:12px; opacity:0.7;'>SAĞLIK PUANI</div>
                    <div style='font-size:64px; font-weight:700;'>{data['puan']}</div>
                    <div style='color:{renk}'>{'MÜKEMMEL' if data['puan']>=80 else 'İYİ / ORTA'}</div>
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
        
        # 3. GRAFİK
        st.markdown("<br><div class='reveal-3'>", unsafe_allow_html=True)
        st.markdown("### 📉 Fiyat Hareketi")
        fig = go.Figure(data=[go.Candlestick(x=data['hist'].index, open=data['hist']['Open'], 
                        high=data['hist']['High'], low=data['hist']['Low'], close=data['hist']['Close'])])
        fig.update_layout(height=400, template="plotly_white", margin=dict(t=30, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # 4. AI
        st.markdown("<br><div class='reveal-4'>", unsafe_allow_html=True)
        st.markdown("### 🧠 ODAK Görüşü")
        yorum = ai_analiz(data)
        st.markdown(f"<div class='ai-box'>{yorum}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

else:
    st.markdown("<br><br><h1 style='text-align:center;'>🎯 ODAK</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#666;'>Analiz için sol menüden hisse seçin.</p>", unsafe_allow_html=True)
