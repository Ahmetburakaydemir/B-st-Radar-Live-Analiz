import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from groq import Groq
import re

# --- 1. SAYFA AYARLARI ---
st.set_page_config(
    page_title="ODAK | Premium",
    page_icon="🎯",
    layout="wide"
)

# --- 2. GURU CSS: PIANO WHITE & SOFT LUXURY ---
st.markdown("""
    <style>
    /* Ana Arka Plan: Soft Beyaz */
    .stApp {
        background-color: #F5F7F8;
        color: #111111;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    
    /* Metrik Kutuları (Beyaz Kartlar) */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E0E0E0;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05); /* Çok hafif gölge */
    }
    
    /* Metrik Yazıları (Piano Black) */
    div[data-testid="stMetric"] label {
        color: #666666 !important; /* Başlıklar Gri */
        font-weight: 500;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #111111 !important; /* Değerler Simsiyah */
        font-weight: 700;
    }
    
    /* F-RAY Puan Kutusu (Kontrast İçin Siyah Bıraktık - Lüks Dursun) */
    .score-box {
        background: linear-gradient(135deg, #111111 0%, #2c3e50 100%);
        color: white;
        border-radius: 15px;
        padding: 25px;
        text-align: center;
        box-shadow: 0 10px 25px rgba(0,0,0,0.2);
    }
    .score-val { font-size: 48px; font-weight: 800; color: #FFFFFF; }
    .score-label { font-size: 13px; color: #B0B0B0; letter-spacing: 2px; text-transform: uppercase; margin-top: 5px;}
    
    /* AI Kutusu (Minimalist Gri) */
    .ai-box {
        background-color: #FFFFFF;
        border-left: 4px solid #111111; /* Siyah Çizgi */
        padding: 25px;
        border-radius: 0 12px 12px 0;
        color: #333333;
        font-size: 16px;
        line-height: 1.7;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    }
    
    /* Başlıklar */
    h1, h2, h3 { color: #111111 !important; letter-spacing: -0.5px; }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E0E0E0;
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

# --- 5. GÜÇLENDİRİLMİŞ VERİ MOTORU (YENİ!) ---
def rsi_hesapla(data, window=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def veri_getir(sembol):
    """
    Bu fonksiyon artık '0' gelen verileri tamir etmeye çalışır.
    """
    try:
        hisse = yf.Ticker(sembol)
        
        # 1. Yöntem: Standart Bilgi
        bilgi = hisse.info
        
        # 2. Yöntem: Fast Info (Daha güvenilir fiyat için)
        fast_info = hisse.fast_info
        
        # Fiyatı garantileme
        guncel_fiyat = bilgi.get('currentPrice')
        if guncel_fiyat is None:
            guncel_fiyat = fast_info.last_price # Yedek kanal

        if guncel_fiyat is None: return None # Fiyat yoksa işlem yapamayız

        # Verileri "None" ise "0" yapma, "-" yap veya hesapla
        def guvenli_al(anahtar, varsayilan=0):
            deger = bilgi.get(anahtar)
            return varsayilan if deger is None else deger

        fk = guvenli_al('trailingPE', 0)
        # Eğer F/K sıfır geldiyse ve EPS varsa, manuel hesapla
        if fk == 0:
            eps = guvenli_al('trailingEps', 0)
            if eps != 0:
                fk = guncel_fiyat / eps

        pd_dd = guvenli_al('priceToBook', 0)
        roe = guvenli_al('returnOnEquity', 0) * 100
        buyume = guvenli_al('revenueGrowth', 0) * 100
        
        # Tarihsel Veri
        hist = hisse.history(period="1y")
        hist['RSI'] = rsi_hesapla(hist)
        son_rsi = hist['RSI'].iloc[-1]
        
        # Değişim Hesapla
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
        elif buyume > 0: puan += 10
        
        return {
            'ad': bilgi.get('longName', sembol),
            'fiyat': guncel_fiyat,
            'fk': fk,
            'pd_dd': pd_dd,
            'roe': roe,
            'buyume': buyume,
            'rsi': son_rsi,
            'degisim': degisim,
            'puan': min(puan, 100),
            'hist': hist
        }
    except Exception as e:
        print(f"Veri Hatası: {e}") # Konsola yaz
        return None

def metni_temizle(metin):
    metin = re.sub(r'[^\x00-\x7F\u00C0-\u00FF\u0100-\u017F\s.,;:!?()"\'-]', '', metin)
    yasakli = ["approximately", "slightly", "doing", "trading", "However", "overall"]
    for k in yasakli: metin = metin.replace(k, "").replace(k.lower(), "")
    return metin

@st.cache_data(ttl=0, show_spinner=False)
def ai_analiz(mod, veri1, veri2=None):
    try:
        if mod == 'TEK':
            prompt = f"""
            GÖREV: {veri1['ad']} hissesini Türkçe analiz et.
            VERİLER: Fiyat: {veri1['fiyat']:.2f}, F/K: {veri1['fk']:.2f}, ROE: %{veri1['roe']:.1f}, Puan: {veri1['puan']}/100.
            KURALLAR: Asla yabancı karakter kullanma. İstanbul Türkçesi ile, bir mentor gibi konuş. 
            """
        else:
            prompt = f"""
            GÖREV: {veri1['ad']} vs {veri2['ad']} kıyasla.
            """
        chat = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.1
        )
        return metni_temizle(chat.choices[0].message.content)
    except Exception as e: return f"AI Hatası: {str(e)}"

# --- 6. ARAYÜZ ---
c1, c2 = st.columns([1, 10])
with c1: st.image("https://cdn-icons-png.flaticon.com/512/3281/3281306.png", width=60) # Siyah hedef ikonu
with c2: 
    st.markdown("<h1 style='margin-bottom:0; padding-bottom:0;'>ODAK AI</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #666; font-size: 16px;'>Akıllı Yatırım & Karar Destek Sistemi</p>", unsafe_allow_html=True)
st.markdown("---")

# Sidebar
st.sidebar.markdown("### ⚙️ Kontrol Paneli")
list_secenekler = [f"{k} - {v}" for k, v in BIST_SIRKETLERI.items()]
secim1 = st.sidebar.selectbox("Hisse Seçiniz", list_secenekler, index=0)
kod1 = secim1.split(" - ")[0] + ".IS"

if st.sidebar.button("ANALİZ ET"):
    with st.spinner('ODAK motoru çalışıyor...'):
        data = veri_getir(kod1)
        if not data:
            st.error("Veri alınamadı. Borsa kapalı veya kaynakta sorun olabilir.")
            st.stop()
            
        # --- ÜST KISIM: PUAN VE METRİKLER ---
        col_score, col_metrics = st.columns([1, 3])
        
        with col_score:
            renk = "#2ecc71" if data['puan'] >= 80 else ("#f1c40f" if data['puan'] >= 50 else "#e74c3c")
            durum = "MÜKEMMEL" if data['puan'] >= 80 else ("İYİ / ORTA" if data['puan'] >= 50 else "ZAYIF")
            
            # F-Ray Siyah Kutu (Beyaz temada kontrast yaratır)
            st.markdown(f"""
            <div class='score-box'>
                <div class='score-label'>ODAK PUANI</div>
                <div class='score-val'>{data['puan']}</div>
                <div class='score-label' style='color:{renk}'>{durum}</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col_metrics:
            m1, m2, m3 = st.columns(3)
            m1.metric("Fiyat", f"{data['fiyat']:.2f} ₺", f"%{data['degisim']:.2f}")
            
            # F/K 0 ise 'A/D' (Anlamlı Değil) yaz
            fk_gosterim = f"{data['fk']:.2f}" if data['fk'] > 0 else "A/D"
            m1.metric("F/K Oranı", fk_gosterim)
            
            m2.metric("ROE (Karlılık)", f"%{data['roe']:.1f}")
            m2.metric("Büyüme", f"%{data['buyume']:.1f}")
            
            m3.metric("RSI", f"{data['rsi']:.1f}")
            m3.metric("PD/DD", f"{data['pd_dd']:.2f}")

        st.markdown("---")
        
        # --- ALT KISIM: GRAFİK VE AI ---
        g1, g2 = st.columns([2, 1])
        
        with g1:
            st.markdown("#### 📉 Fiyat Grafiği")
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=data['hist'].index, open=data['hist']['Open'], 
                                         high=data['hist']['High'], low=data['hist']['Low'], 
                                         close=data['hist']['Close'], name=data['ad']))
            # Grafik de açık renk olsun
            fig.update_layout(height=400, template="plotly_white", margin=dict(t=20, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
        
        with g2:
            st.markdown("#### 🧠 Analist Notu")
            yorum = ai_analiz('TEK', data)
            st.markdown(f"<div class='ai-box'>{yorum}</div>", unsafe_allow_html=True)
