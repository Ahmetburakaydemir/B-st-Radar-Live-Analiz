import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from groq import Groq
import re

# --- 1. SAYFA AYARLARI (MINIMALIST) ---
st.set_page_config(
    page_title="BIST Radar", # "Pro" gibi ekleri attık, sadeleşti.
    page_icon="📈", # Elmas gitti, ciddi grafik geldi.
    layout="wide"
)

# --- 2. GURU CSS: QUIET LUXURY TASARIM ---
# Burası uygulamanın makyajını yapan kısım.
st.markdown("""
    <style>
    /* 1. Arka Planı ve Genel Fontu Ayarla */
    .stApp {
        background-color: #0E1117; /* Çok koyu antrasit */
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    
    /* 2. Metrik Kutuları (Sade Lüks) */
    div[data-testid="stMetric"] {
        background-color: #161B22; /* Ana arka plandan bir tık açık */
        border: 1px solid #30363D; /* Çok ince, zarif çerçeve */
        padding: 15px;
        border-radius: 8px; /* Yumuşak köşeler */
        color: white;
    }
    
    /* 3. Metrik Yazı Renklerini ZORLA Beyaz Yap (Okunmama sorununu çözer) */
    div[data-testid="stMetric"] label {
        color: #8B949E !important; /* Başlıklar (Örn: Fiyat) Duman Grisi */
        font-size: 14px;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #F0F6FC !important; /* Değerler (Örn: 270 TL) Kırık Beyaz */
        font-weight: 600;
    }
    
    /* 4. Başlıklar */
    h1, h2, h3 {
        color: #F0F6FC !important;
        font-weight: 300; /* İnce ve zarif font */
        letter-spacing: -0.5px;
    }
    
    /* 5. Butonlar (Minimalist) */
    .stButton > button {
        background-color: #238636; /* Mat Yeşil */
        color: white;
        border: none;
        border-radius: 6px;
        padding: 10px 20px;
        font-weight: 500;
    }
    .stButton > button:hover {
        background-color: #2EA043;
    }

    /* 6. AI Kutusu (Renkli kutular yerine sade yazı) */
    .ai-box {
        background-color: #161B22;
        border-left: 3px solid #D29922; /* Mat Altın Sarısı Çizgi */
        padding: 20px;
        border-radius: 4px;
        color: #E6EDF3;
        font-size: 16px;
        line-height: 1.6;
        margin-top: 20px;
        margin-bottom: 20px;
    }
    
    /* 7. Spinner Rengi */
    .stSpinner > div {
        border-top-color: #D29922 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SABİT VERİLER ---
BIST_SIRKETLERI = {
    "THYAO": "TÜRK HAVA YOLLARI",
    "PGSUS": "PEGASUS",
    "GARAN": "GARANTİ BBVA",
    "AKBNK": "AKBANK",
    "YKBNK": "YAPI KREDİ",
    "ISCTR": "İŞ BANKASI (C)",
    "ASELS": "ASELSAN",
    "KCHOL": "KOÇ HOLDİNG",
    "SAHOL": "SABANCI HOLDİNG",
    "EREGL": "EREĞLİ DEMİR ÇELİK",
    "SISE": "ŞİŞECAM",
    "BIMAS": "BİM MAĞAZALAR",
    "MGROS": "MİGROS",
    "TUPRS": "TÜPRAŞ",
    "PETKM": "PETKİM",
    "FROTO": "FORD OTOSAN",
    "TOASO": "TOFAŞ OTO",
    "TCELL": "TURKCELL",
    "TTKOM": "TÜRK TELEKOM",
    "SASA": "SASA POLYESTER",
    "HEKTS": "HEKTAŞ",
    "ENKAI": "ENKA İNŞAAT",
    "VESTL": "VESTEL",
    "ARCLK": "ARÇELİK",
    "KONTR": "KONTROLMATİK",
    "ASTOR": "ASTOR ENERJİ",
    "KOZAL": "KOZA ALTIN",
    "ODAS": "ODAŞ ELEKTRİK",
    "EKGYO": "EMLAK KONUT"
}

# --- 4. API KURULUMU ---
try:
    api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=api_key)
except Exception:
    st.error("⚠️ API Key Hatası.")
    st.stop()

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
        hist = hisse.history(period="1y")
        
        if 'currentPrice' not in bilgi: return None
            
        data = {
            'fiyat': bilgi.get('currentPrice'),
            'fk': bilgi.get('trailingPE', 0),
            'pd_dd': bilgi.get('priceToBook', 0),
            'roe': bilgi.get('returnOnEquity', 0) * 100,
            'ad': bilgi.get('longName', sembol),
            'hist': hist
        }
        
        data['hist']['RSI'] = rsi_hesapla(data['hist'])
        data['rsi'] = data['hist']['RSI'].iloc[-1]
        onceki_kapanis = data['hist']['Close'].iloc[-2]
        data['degisim'] = ((data['fiyat'] - onceki_kapanis) / onceki_kapanis) * 100
        
        return data
    except: return None

def metni_temizle(metin):
    metin = re.sub(r'[^\x00-\x7F\u00C0-\u00FF\u0100-\u017F\s.,;:!?()"\'-]', '', metin)
    yasakli = ["approximately", "slightly", "doing", "trading", "However", "overall"]
    for kelime in yasakli:
        metin = metin.replace(kelime, "").replace(kelime.lower(), "")
    return metin

@st.cache_data(ttl=0, show_spinner=False)
def ai_analiz(mod, veri1, veri2=None):
    try:
        if mod == 'TEK':
            prompt = f"""
            GÖREV: {veri1['ad']} hissesini Türkçe analiz et.
            VERİLER: Fiyat: {veri1['fiyat']}, F/K: {veri1['fk']:.2f}, ROE: %{veri1['roe']:.1f}, RSI: {veri1['rsi']:.1f}.
            KURALLAR: Asla yabancı karakter kullanma. İstanbul Türkçesi ile, bir mentor gibi konuş. 
            Başlıkları '1. GENEL', '2. ANLAM', '3. SONUÇ' gibi sade tut.
            """
        else:
            prompt = f"""
            GÖREV: {veri1['ad']} vs {veri2['ad']} kıyasla.
            1. {veri1['ad']}: F/K {veri1['fk']:.2f}, ROE %{veri1['roe']:.1f}
            2. {veri2['ad']}: F/K {veri2['fk']:.2f}, ROE %{veri2['roe']:.1f}
            Sadece Türkçe yaz. Hangisi ucuz, hangisi karlı net söyle.
            """
        
        chat = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.1
        )
        return metni_temizle(chat.choices[0].message.content)
    except Exception as e:
        return f"AI Hatası: {str(e)}"

# --- 6. ARAYÜZ ---

# Başlık (Sade)
st.title("BIST Radar")
st.markdown("<p style='color: #8B949E; margin-top: -15px;'>Akıllı Finansal Karar Destek Sistemi</p>", unsafe_allow_html=True)
st.markdown("---")

# Sidebar
st.sidebar.header("Ayarlar")
list_secenekler = [f"{k} - {v}" for k, v in BIST_SIRKETLERI.items()]
secim1 = st.sidebar.selectbox("Ana Hisse", list_secenekler, index=0)
kod1 = secim1.split(" - ")[0] + ".IS"

kiyaslama_modu = st.sidebar.checkbox("Kıyaslama Modu")
kod2 = None

if kiyaslama_modu:
    secim2 = st.sidebar.selectbox("Rakip Hisse", list_secenekler, index=1)
    kod2 = secim2.split(" - ")[0] + ".IS"
    analyze_btn_text = "Karşılaştır"
else:
    analyze_btn_text = "Analiz Et"

# Buton
if st.sidebar.button(analyze_btn_text):
    with st.spinner('Analiz yapılıyor...'):
        data1 = veri_getir(kod1)
        if not data1: st.stop()

        if kiyaslama_modu and kod2:
            data2 = veri_getir(kod2)
            if not data2: st.stop()
            
            # --- DÜELLO ---
            st.subheader(f"{data1['ad']} vs {data2['ad']}")
            c1, c2 = st.columns(2)
            
            with c1:
                st.markdown(f"**{data1['ad']}**")
                st.metric("Fiyat", f"{data1['fiyat']} ₺", f"%{data1['degisim']:.2f}")
                st.metric("F/K", f"{data1['fk']:.2f}")
                st.metric("ROE", f"%{data1['roe']:.1f}")
            
            with c2:
                st.markdown(f"**{data2['ad']}**")
                st.metric("Fiyat", f"{data2['fiyat']} ₺", f"%{data2['degisim']:.2f}")
                st.metric("F/K", f"{data2['fk']:.2f}")
                st.metric("ROE", f"%{data2['roe']:.1f}")
            
            # AI Yorumu (Custom Box)
            yorum = ai_analiz('DUELLO', data1, data2)
            st.markdown(f"<div class='ai-box'><b>🤖 Yapay Zeka Görüşü:</b><br><br>{yorum}</div>", unsafe_allow_html=True)
            
        else:
            # --- TEKLİ ---
            st.subheader(f"{data1['ad']}")
            
            # Metrikler
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Fiyat", f"{data1['fiyat']} ₺", f"%{data1['degisim']:.2f}")
            k2.metric("F/K", f"{data1['fk']:.2f}")
            k3.metric("ROE", f"%{data1['roe']:.1f}")
            k4.metric("RSI", f"{data1['rsi']:.1f}")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Grafik ve Yorum
            g1, g2 = st.columns([2, 1])
            
            with g1:
                fig = go.Figure()
                fig.add_trace(go.Candlestick(x=data1['hist'].index, open=data1['hist']['Open'], 
                                             high=data1['hist']['High'], low=data1['hist']['Low'], 
                                             close=data1['hist']['Close'], name=data1['ad']))
                # Grafik Ayarları (Mat Siyah)
                fig.update_layout(height=450, template="plotly_dark", 
                                  paper_bgcolor="#161B22", plot_bgcolor="#161B22",
                                  margin=dict(l=0, r=0, t=20, b=0))
                st.plotly_chart(fig, use_container_width=True)
            
            with g2:
                yorum = ai_analiz('TEK', data1)
                # Buradaki HTML ile kendi "Sade Lüks" kutumuzu yapıyoruz
                st.markdown(f"<div class='ai-box'><b>Analist Notu:</b><br><br>{yorum}</div>", unsafe_allow_html=True)
# --- SIDEBAR ALTINA İMZA EKLEME ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 🛠️ Tech Stack")
st.sidebar.info(
    """
    Bu proje aşağıdaki teknolojilerle geliştirilmiştir:
    
    * 🐍 **Python 3.9**
    * 📊 **Streamlit Framework**
    * 🧠 **LLM:** Meta Llama-3 (via Groq)
    * 📡 **Veri:** Yahoo Finance API
    * 📈 **Görsel:** Plotly Express
    """
)
st.sidebar.markdown(f"<div style='text-align: center; color: #8B949E; font-size: 12px;'>Geliştirici: [Ahmet Burak Aydemir] © 2025</div>", unsafe_allow_html=True)

