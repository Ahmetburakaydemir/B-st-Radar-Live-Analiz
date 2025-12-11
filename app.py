import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from groq import Groq
import re

# --- 1. SAYFA AYARLARI ---
st.set_page_config(
    page_title="ODAK | Akıllı Yatırım",
    page_icon="🎯", # Hedef ikonu
    layout="wide"
)

# --- 2. TASARIM: QUIET LUXURY (ODAK KONSEPTİ) ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; font-family: 'Helvetica Neue', sans-serif; }
    
    /* Puan Kutusu Tasarımı (F-RAY) */
    .score-box {
        background: linear-gradient(135deg, #161B22 0%, #0E1117 100%);
        border: 1px solid #30363D;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    .score-val { font-size: 42px; font-weight: 700; color: #F0F6FC; }
    .score-label { font-size: 14px; color: #8B949E; letter-spacing: 1px; text-transform: uppercase; }
    
    /* Metrikler */
    div[data-testid="stMetric"] { background-color: #161B22; border: 1px solid #21262D; border-radius: 8px; }
    div[data-testid="stMetric"] label { color: #8B949E !important; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #F0F6FC !important; }
    
    /* AI Kutusu */
    .ai-box {
        border-left: 3px solid #238636; /* ODAK Yeşili */
        background-color: #161B22; padding: 20px; border-radius: 0 8px 8px 0; color: #E6EDF3;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. GENİŞLETİLMİŞ HİSSE LİSTESİ (BIST 100+) ---
# Buraya en popüler 50-60 hisseyi koydum, listenin kalabalıklığı gözünü korkutmasın.
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
    "EKGYO": "EMLAK KONUT", "GUBRF": "GÜBRE FABRİKALARI", "SOKM": "ŞOK MARKETLER",
    "MGROS": "MİGROS", "AEFES": "ANADOLU EFES", "AGHOL": "AG ANADOLU GRUBU",
    "AKSEN": "AKSA ENERJİ", "ALARK": "ALARKO HOLDİNG", "ARZUM": "ARZUM EV ALETLERİ",
    "BIOEN": "BIOTREND ENERJİ", "BRSAN": "BORUSAN", "CANTE": "ÇAN2 TERMİK",
    "CCOLA": "COCA COLA İÇECEK", "CEMTS": "ÇEMTAŞ", "CIMSA": "ÇİMSA",
    "DOAS": "DOĞUŞ OTOMOTİV", "EGEEN": "EGE ENDÜSTRİ", "ENJSA": "ENERJİSA",
    "GESAN": "GİRİŞİM ELEKTRİK", "GLYHO": "GLOBAL YATIRIM HOLDİNG",
    "HALKB": "HALKBANK", "ISGYO": "İŞ GYO", "ISMEN": "İŞ YATIRIM",
    "KORDS": "KORDSA", "MAVI": "MAVİ GİYİM", "OTKAR": "OTOKAR",
    "OYAKC": "OYAK ÇİMENTO", "QUAGR": "QUA GRANITE", "SMRTG": "SMART GÜNEŞ",
    "TAVHL": "TAV HAVALİMANLARI", "TKFEN": "TEKFEN HOLDİNG", "TTRAK": "TÜRK TRAKTÖR",
    "ULKER": "ÜLKER BİSKÜVİ", "VESBE": "VESTEL BEYAZ EŞYA", "ZOREN": "ZORLU ENERJİ"
}

# --- 4. API VE HESAPLAMA MOTORU ---
try:
    api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=api_key)
except: st.error("API Key Hatası"); st.stop()

def rsi_hesapla(data, window=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# --- YENİLİK: F-RAY PUANLAMA MOTORU (STEVE JOBS DOKUNUŞU) ---
def f_ray_puani_hesapla(fk, roe, rsi, buyume):
    puan = 0
    
    # 1. Karlılık (ROE) - En önemlisi
    if roe > 40: puan += 30
    elif roe > 20: puan += 20
    elif roe > 10: puan += 10
    
    # 2. Ucuzluk (F/K)
    if 0 < fk < 8: puan += 30
    elif 8 <= fk < 15: puan += 20
    elif 15 <= fk < 25: puan += 10
    
    # 3. Teknik (RSI)
    if 30 <= rsi <= 60: puan += 20 # Güvenli bölge
    elif 60 < rsi < 80: puan += 10 # Yükseliş trendi
    
    # 4. Büyüme
    if buyume > 50: puan += 20
    elif buyume > 10: puan += 10
    
    return min(puan, 100) # Max 100

def get_puan_rengi(puan):
    if puan >= 80: return "#238636", "MÜKEMMEL" # Yeşil
    elif puan >= 50: return "#D29922", "İYİ / MAKUL" # Sarı
    else: return "#DA3633", "RİSKLİ / ZAYIF" # Kırmızı

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
            'buyume': bilgi.get('revenueGrowth', 0) * 100,
            'ad': bilgi.get('longName', sembol),
            'hist': hist
        }
        data['hist']['RSI'] = rsi_hesapla(data['hist'])
        data['rsi'] = data['hist']['RSI'].iloc[-1]
        
        # F-RAY Puanını Hesapla
        data['puan'] = f_ray_puani_hesapla(data['fk'], data['roe'], data['rsi'], data['buyume'])
        
        onceki_kapanis = data['hist']['Close'].iloc[-2]
        data['degisim'] = ((data['fiyat'] - onceki_kapanis) / onceki_kapanis) * 100
        return data
    except: return None

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
            VERİLER: Fiyat: {veri1['fiyat']}, F/K: {veri1['fk']:.2f}, ROE: %{veri1['roe']:.1f}, Büyüme: %{veri1['buyume']:.1f}.
            ÖNEMLİ: Hissenin 'F-Ray Puanı' 100 üzerinden {veri1['puan']} çıkmıştır.
            Buna göre, puanı düşükse nedenlerini, yüksekse avantajlarını anlat.
            Sadece Türkçe yaz. Doğal ve akıcı bir mentor dili kullan.
            """
        else:
            prompt = f"""
            GÖREV: {veri1['ad']} (Puan: {veri1['puan']}) vs {veri2['ad']} (Puan: {veri2['puan']}) kıyasla.
            Veriler: 
            1. {veri1['ad']}: F/K {veri1['fk']:.2f}, ROE %{veri1['roe']:.1f}
            2. {veri2['ad']}: F/K {veri2['fk']:.2f}, ROE %{veri2['roe']:.1f}
            Sadece Türkçe yaz. Hangisi yatırımcı için daha cazip söyle.
            """
        chat = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.1
        )
        return metni_temizle(chat.choices[0].message.content)
    except Exception as e: return f"Hata: {str(e)}"

# --- 5. ARAYÜZ ---
# Header
c1, c2 = st.columns([1, 6])
with c1: st.title("🎯") 
with c2: 
    st.title("ODAK")
    st.markdown("<p style='color: #8B949E; margin-top: -20px; font-size: 14px;'>Yapay Zeka Destekli Borsa Asistanı</p>", unsafe_allow_html=True)
st.markdown("---")

# Sidebar
st.sidebar.markdown("### ⚙️ Analiz Ayarları")
list_secenekler = [f"{k} - {v}" for k, v in BIST_SIRKETLERI.items()]
secim1 = st.sidebar.selectbox("Odaklanılan Hisse", list_secenekler, index=0)
kod1 = secim1.split(" - ")[0] + ".IS"

kiyaslama_modu = st.sidebar.checkbox("Kıyaslama Modu (Düello)")
kod2 = None

if kiyaslama_modu:
    secim2 = st.sidebar.selectbox("Rakip Hisse", list_secenekler, index=1)
    kod2 = secim2.split(" - ")[0] + ".IS"
    analyze_btn_text = "⚔️ KARŞILAŞTIR"
else:
    analyze_btn_text = "✨ ANALİZ ET"

# --- SIDEBAR TECH STACK ---
st.sidebar.markdown("---")
st.sidebar.markdown("<p style='font-size: 12px; color: #555;'>POWERED BY</p>", unsafe_allow_html=True)
st.sidebar.markdown("`Python` `Streamlit` `Llama-3`")

if st.sidebar.button(analyze_btn_text):
    with st.spinner('Piyasa verileri işleniyor ve F-Ray puanı hesaplanıyor...'):
        data1 = veri_getir(kod1)
        if not data1: st.stop()

        if kiyaslama_modu and kod2:
            data2 = veri_getir(kod2)
            if not data2: st.stop()
            
            # --- DÜELLO SAYFASI ---
            col1, col2 = st.columns(2)
            
            # Ana Hisse Kartı
            with col1:
                renk1, durum1 = get_puan_rengi(data1['puan'])
                st.markdown(f"""
                <div class='score-box' style='border-top: 4px solid {renk1};'>
                    <div class='score-label'>{data1['ad']}</div>
                    <div class='score-val' style='color: {renk1}'>{data1['puan']}</div>
                    <div class='score-label'>{durum1}</div>
                </div>
                """, unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                st.metric("Fiyat", f"{data1['fiyat']} ₺", f"%{data1['degisim']:.2f}")
                st.metric("ROE (Karlılık)", f"%{data1['roe']:.1f}")
            
            # Rakip Hisse Kartı
            with col2:
                renk2, durum2 = get_puan_rengi(data2['puan'])
                st.markdown(f"""
                <div class='score-box' style='border-top: 4px solid {renk2};'>
                    <div class='score-label'>{data2['ad']}</div>
                    <div class='score-val' style='color: {renk2}'>{data2['puan']}</div>
                    <div class='score-label'>{durum2}</div>
                </div>
                """, unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                st.metric("Fiyat", f"{data2['fiyat']} ₺", f"%{data2['degisim']:.2f}")
                st.metric("ROE (Karlılık)", f"%{data2['roe']:.1f}")

            st.markdown("---")
            yorum = ai_analiz('DUELLO', data1, data2)
            st.markdown(f"<div class='ai-box'><b>⚔️ ODAK Karşılaştırması:</b><br><br>{yorum}</div>", unsafe_allow_html=True)

        else:
            # --- TEKLİ ANALİZ SAYFASI ---
            
            # 1. BÖLÜM: F-RAY SKOR KARTI (YENİ STEVE JOBS ÖZELLİĞİ)
            puan_renk, puan_durum = get_puan_rengi(data1['puan'])
            
            c_score, c_metrics = st.columns([1, 2])
            
            with c_score:
                st.markdown(f"""
                <div class='score-box'>
                    <div class='score-label'>F-RAY SAĞLIK PUANI</div>
                    <div class='score-val' style='color: {puan_renk}'>{data1['puan']}<span style='font-size:20px'>/100</span></div>
                    <div class='score-label' style='color: {puan_renk}; border: 1px solid {puan_renk}; padding: 4px; border-radius: 4px; display: inline-block; margin-top: 5px;'>{puan_durum}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with c_metrics:
                m1, m2, m3 = st.columns(3)
                m1.metric("Anlık Fiyat", f"{data1['fiyat']} ₺", f"%{data1['degisim']:.2f}")
                m1.metric("F/K Oranı", f"{data1['fk']:.2f}")
                
                m2.metric("ROE (Karlılık)", f"%{data1['roe']:.1f}")
                m2.metric("Yıllık Büyüme", f"%{data1['buyume']:.1f}")
                
                rsi_val = data1['rsi']
                rsi_col = "inverse" if rsi_val > 70 else "normal"
                m3.metric("RSI (Teknik)", f"{rsi_val:.1f}", delta_color=rsi_col)
                m3.metric("PD/DD", f"{data1['pd_dd']:.2f}")

            st.markdown("---")

            # 2. BÖLÜM: GRAFİK VE AI
            g1, g2 = st.columns([2, 1])
            
            with g1:
                st.markdown("##### 📉 Fiyat Grafiği")
                fig = go.Figure()
                fig.add_trace(go.Candlestick(x=data1['hist'].index, open=data1['hist']['Open'], 
                                             high=data1['hist']['High'], low=data1['hist']['Low'], 
                                             close=data1['hist']['Close'], name=data1['ad']))
                fig.update_layout(height=400, template="plotly_dark", 
                                  paper_bgcolor="#161B22", plot_bgcolor="#161B22", 
                                  margin=dict(l=0, r=0, t=10, b=0))
                st.plotly_chart(fig, use_container_width=True)
            
            with g2:
                st.markdown("##### 🧠 ODAK Analizi")
                yorum = ai_analiz('TEK', data1)
                st.markdown(f"<div class='ai-box'>{yorum}</div>", unsafe_allow_html=True)
