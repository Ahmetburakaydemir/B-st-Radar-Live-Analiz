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
    /* GENEL FONT VE ARKA PLAN */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    .stApp {
        background-color: #FBFBFD;
        font-family: 'Inter', sans-serif;
        color: #1D1D1F;
    }

    /* --- SIDEBAR ÖZEL TASARIM (İstediğin Renk) --- */
    section[data-testid="stSidebar"] {
        background-color: #8B0000; /* Koyu Bordo */
    }
    
    /* Sidebar içindeki tüm yazıları BEYAZ yap */
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3, 
    section[data-testid="stSidebar"] label, 
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] div,
    section[data-testid="stSidebar"] p {
        color: #FFFFFF !important;
    }
    
    /* Sidebar Selectbox İyileştirme */
    div[data-testid="stSidebar"] .stSelectbox > div > div {
        background-color: rgba(255,255,255,0.1);
        color: white;
        border: 1px solid rgba(255,255,255,0.2);
    }

    /* Sidebar Butonu */
    div[data-testid="stSidebar"] .stButton > button {
        background-color: #FFFFFF;
        color: #8B0000;
        font-weight: bold;
        border: none;
        width: 100%;
    }
    div[data-testid="stSidebar"] .stButton > button:hover {
        background-color: #f0f0f0;
        color: #a00000;
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

    /* --- HERO & METRİKLER --- */
    .hero-container { padding: 40px 0; text-align: center; margin-bottom: 30px; }
    .company-title { font-size: 52px; font-weight: 700; color: #1D1D1F; letter-spacing: -1.5px; }
    .company-sector { font-size: 18px; color: #86868B; text-transform: uppercase; letter-spacing: 1px; }
    
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.9);
        border: 1px solid rgba(0,0,0,0.08);
        border-radius: 16px;
        padding: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }

    /* F-RAY PUAN KUTUSU (Minimalist Siyah) */
    .score-container {
        text-align: center;
        background: #1D1D1F;
        color: white;
        padding: 25px;
        border-radius: 20px;
        box-shadow: 0 15px 40px rgba(0,0,0,0.2);
    }
    
    /* AI KUTUSU */
    .ai-box {
        background-color: #FFFFFF;
        border-radius: 16px;
        padding: 30px;
        border: 1px solid rgba(0,0,0,0.05);
        box-shadow: 0 4px 20px rgba(0,0,0,0.03);
        line-height: 1.8;
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
        
        ozet = bilgi.get('longBusinessSummary', 'Şirket açıklaması bulunamadı.')
        sektor = bilgi.get('sector', 'Genel')
        
        return {
            'ad': bilgi.get('longName', sembol),
            'fiyat': guncel_fiyat, 'fk': fk, 'pd_dd': pd_dd,
            'roe': roe, 'buyume': buyume, 'rsi': son_rsi,
            'degisim': degisim, 'puan': min(puan, 100),
            'hist': hist, 'ozet': ozet, 'sektor': sektor
        }
    except Exception: return None

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
        1. KISIM: İngilizce özeti ({veri['ozet'][:200]}...) baz alarak şirketin ne yaptığını 1 cümleyle Türkçe anlat.
        2. KISIM: Verileri yorumla (Fiyat: {veri['fiyat']}, F/K: {veri['fk']:.2f}, ROE: %{veri['roe']:.1f}).
        KURALLAR: Başlık kullanma. Çok akıcı, hikaye anlatır gibi Türkçe konuş.
        """
        chat = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.1
        )
        return metni_temizle(chat.choices[0].message.content)
    except Exception as e: return f"AI Hatası: {str(e)}"

# --- 6. ARAYÜZ ---
# SIDEBAR (Bordo & Beyaz)
st.sidebar.markdown("### 🎯 ODAK")
list_secenekler = [f"{k} - {v}" for k, v in BIST_SIRKETLERI.items()]
secim1 = st.sidebar.selectbox("Hisse Seçiniz", list_secenekler, index=0)
kod1 = secim1.split(" - ")[0] + ".IS"
analyze_btn = st.sidebar.button("ANALİZİ BAŞLAT")

# --- YENİ EKLENEN: FİNANSAL SÖZLÜK (Hap Bilgiler) ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 📚 ODAK AKADEMİ")

with st.sidebar.expander("📝 Bu Terimler Ne Demek?"):
    st.markdown("""
    **💰 F/K (Fiyat/Kazanç):**
    Şirkete yatırdığınız parayı kaç yılda geri alacağınızı gösterir.
    * *Düşük olması (0-10) genelde ucuzluk belirtisidir.*
    
    **🚀 ROE (Özsermaye Karlılığı):**
    Şirketin ortakların parasını ne kadar verimli kullandığını gösterir.
    * *%30 ve üzeri 'Mükemmel' kabul edilir.*
    
    **📊 RSI (Güç Endeksi):**
    Hisse aşırı mı alındı yoksa aşırı mı satıldı?
    * *30 altı: Ucuz (Alım Fırsatı)*
    * *70 üstü: Pahalı (Satış Baskısı)*
    
    **🏢 PD/DD (Piyasa/Defter):**
    Şirketin borsa değeri, muhasebe değerinin kaç katı?
    * *1'e yakın olması istenir.*
    """)

st.sidebar.info("⚠️ **Yasal Uyarı:** Yapay zeka ve veriler hata yapabilir. Buradaki bilgiler yatırım tavsiyesi değildir. Son kararı her zaman siz verin.")


# ANA SAYFA AKIŞI
if analyze_btn:
    with st.spinner('ODAK motoru piyasayı tarıyor...'):
        data = veri_getir(kod1)
        if not data: st.error("Veri alınamadı."); st.stop()
        
        # HERO SECTION
        st.markdown(f"""
        <div class='hero-container reveal-1'>
            <div class='company-sector'>{data['sektor']}</div>
            <div class='company-title'>{data['ad']}</div>
            <div class='company-desc'>
                Güncel Fiyat: <b style='font-size:20px'>{data['fiyat']:.2f} ₺</b> 
                <span style='color: {'#2ecc71' if data['degisim']>0 else '#e74c3c'}; background: rgba(0,0,0,0.05); padding: 5px 10px; border-radius: 20px;'>
                %{data['degisim']:.2f}
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")

        # PUAN VE METRİKLER
        c_score, c_metrics = st.columns([1, 2])
        
        with c_score:
            renk = "#2ecc71" if data['puan'] >= 80 else ("#f1c40f" if data['puan'] >= 50 else "#e74c3c")
            st.markdown(f"""
            <div class='reveal-2'>
                <div class='score-container'>
                    <div style='font-size: 13px; opacity: 0.6; letter-spacing: 2px;'>F-RAY SAĞLIK PUANI</div>
                    <div style='font-size: 72px; font-weight: 700; margin: 5px 0;'>{data['puan']}</div>
                    <div style='color: {renk}; font-weight: 600; letter-spacing: 1px;'>{'MÜKEMMEL' if data['puan']>=80 else 'İYİ / ORTA'}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with c_metrics:
            st.markdown("<div class='reveal-2'>", unsafe_allow_html=True)
            m1, m2 = st.columns(2)
            m1.metric("F/K (Değerleme)", f"{data['fk']:.2f}")
            m1.metric("ROE (Karlılık)", f"%{data['roe']:.1f}")
            m2.metric("Büyüme (Yıllık)", f"%{data['buyume']:.1f}")
            m2.metric("RSI (Teknik)", f"{data['rsi']:.1f}")
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<br><br>", unsafe_allow_html=True)

        # GRAFİK
        st.markdown("<div class='reveal-3'>", unsafe_allow_html=True)
        st.markdown("### 📉 Fiyat Hareketi")
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=data['hist'].index, open=data['hist']['Open'], 
                                     high=data['hist']['High'], low=data['hist']['Low'], 
                                     close=data['hist']['Close'], name=data['ad']))
        fig.update_layout(height=400, template="plotly_white", margin=dict(t=30, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<br><br>", unsafe_allow_html=True)

        # AI YORUMU
        st.markdown("<div class='reveal-4'>", unsafe_allow_html=True)
        st.markdown("### 🧠 ODAK Görüşü")
        yorum = ai_analiz(data)
        st.markdown(f"<div class='ai-box'>{yorum}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

else:
    # AÇILIŞ EKRANI
    st.markdown("""
    <div style='text-align: center; padding-top: 120px;'>
        <div style='font-size: 80px;'>🎯</div>
        <h1 style='color: #1D1D1F; font-size: 56px; font-weight: 700; margin-bottom: 10px;'>Yatırımın Odak Noktası.</h1>
        <p style='color: #86868B; font-size: 22px; max-width: 600px; margin: 0 auto;'>
            Yapay zeka destekli temel ve teknik analiz için sol menüden bir hisse seçin ve analizi başlatın.
        </p>
    </div>
    """, unsafe_allow_html=True)
