import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from groq import Groq
import re # Metin temizliği için Regex kütüphanesi

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="BIST Radar Pro",
    page_icon="💎",
    layout="wide"
)

# --- GURU DOKUNUŞU: ÖZEL CSS İLE GÖRSEL MAKYAJ ---
# Bu blok, uygulamanın standart görünümünü değiştirip "Kart" yapısı kazandırır.
st.markdown("""
    <style>
    /* Metrik Kutularını Güzelleştirme */
    div[data-testid="stMetric"] {
        background-color: #1E1E1E;
        border: 1px solid #333;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
    }
    div[data-testid="stMetric"] label {
        color: #B0B0B0 !important;
    }
    /* Başlıkları Renklendirme */
    h1, h2, h3 {
        color: #00ADB5 !important;
    }
    /* Kenar Çubuğu Rengi */
    section[data-testid="stSidebar"] {
        background-color: #121212;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 1. SABİT LİSTE ---
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

# --- 2. API KURULUMU ---
try:
    api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=api_key)
except Exception:
    st.error("⚠️ API Anahtarı hatası! Secrets kısmını kontrol et.")
    st.stop()

# --- 3. YARDIMCI FONKSİYONLAR ---
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
        
        if 'currentPrice' not in bilgi:
            return None
            
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
    except Exception:
        return None

# --- TEMİZLİK ROBOTU ---
def metni_temizle(metin):
    """AI çıktısındaki bozuk karakterleri ve İngilizce kalıntıları temizler"""
    # 1. Çince/Japonca karakterleri sil
    metin = re.sub(r'[^\x00-\x7F\u00C0-\u00FF\u0100-\u017F\s.,;:!?()"\'-]', '', metin)
    # 2. Gereksiz İngilizce kelimeleri manuel filtrele (Gerekirse artırılabilir)
    yasakli = ["approximately", "slightly", "doing", "trading", "However"]
    for kelime in yasakli:
        metin = metin.replace(kelime, "")
        metin = metin.replace(kelime.lower(), "")
    return metin

# --- AI ANALİZ FONKSİYONU ---
@st.cache_data(ttl=0, show_spinner=False)
def ai_analiz(mod, veri1, veri2=None):
    try:
        if mod == 'TEK':
            prompt = f"""
            GÖREV: {veri1['ad']} hissesini bir finans uzmanı olarak Türkçe analiz et.
            
            VERİLER:
            Fiyat: {veri1['fiyat']} TL
            F/K: {veri1['fk']:.2f} (Sektör ortalaması 8-10)
            PD/DD: {veri1['pd_dd']:.2f}
            ROE: %{veri1['roe']:.1f}
            RSI: {veri1['rsi']:.1f} (30 altı ucuz, 70 üstü pahalı)

            KURALLAR:
            1. Sadece TÜRKÇE yaz. Yabancı karakter kullanma.
            2. "Yatırım tavsiyesi değildir" uyarısını cümlenin içine doğal yedir.
            3. Şirketin durumunu (Ucuz mu/Pahalı mı, Riskli mi?) net bir dille anlat.
            """
        else:
            prompt = f"""
            GÖREV: {veri1['ad']} ve {veri2['ad']} hisselerini kıyasla.

            1. {veri1['ad']}: F/K {veri1['fk']:.2f}, ROE %{veri1['roe']:.1f}, RSI {veri1['rsi']:.1f}
            2. {veri2['ad']}: F/K {veri2['fk']:.2f}, ROE %{veri2['roe']:.1f}, RSI {veri2['rsi']:.1f}

            ANALİZ:
            - Hangisi değerleme olarak daha ucuz?
            - Hangisi sermayesini daha iyi kullanıyor (ROE)?
            - Sadece Türkçe yaz. Kısa ve net ol.
            """
            
        chat = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.1 # Yaratıcılığı kıstık, hata yapma şansı azaldı
        )
        ham_metin = chat.choices[0].message.content
        return metni_temizle(ham_metin) # Temizlik robotunu çalıştır
    except Exception as e:
        return f"AI Hatası: {str(e)}"

# --- 4. ARAYÜZ (GÜZELLEŞTİRİLMİŞ) ---
st.title("💎 BIST Radar Pro")
st.markdown("---")

st.sidebar.header("Ayarlar")
list_secenekler = [f"{k} - {v}" for k, v in BIST_SIRKETLERI.items()]
secim1 = st.sidebar.selectbox("Ana Hisse", list_secenekler, index=0)
kod1 = secim1.split(" - ")[0] + ".IS"

kiyaslama_modu = st.sidebar.checkbox("Kıyaslama Modu (Düello)")
kod2 = None

if kiyaslama_modu:
    secim2 = st.sidebar.selectbox("Rakip Hisse", list_secenekler, index=1)
    kod2 = secim2.split(" - ")[0] + ".IS"
    analyze_btn_text = "⚔️ DÜELLOYU BAŞLAT"
else:
    analyze_btn_text = "✨ ANALİZ ET"

if st.sidebar.button(analyze_btn_text):
    with st.spinner('Piyasa verileri işleniyor...'):
        data1 = veri_getir(kod1)
        if not data1:
            st.error("Veri hatası.")
            st.stop()

        if kiyaslama_modu and kod2:
            data2 = veri_getir(kod2)
            if not data2:
                st.error("Rakip verisi hatası.")
                st.stop()
            
            # --- DÜELLO EKRANI ---
            st.subheader(f"{data1['ad']} vs {data2['ad']}")
            
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"### 🔹 {data1['ad']}")
                st.metric("Fiyat", f"{data1['fiyat']} ₺", f"%{data1['degisim']:.2f}")
                st.metric("F/K", f"{data1['fk']:.2f}")
                st.metric("ROE", f"%{data1['roe']:.1f}")
                st.metric("RSI", f"{data1['rsi']:.1f}")
            
            with c2:
                st.markdown(f"### 🔸 {data2['ad']}")
                st.metric("Fiyat", f"{data2['fiyat']} ₺", f"%{data2['degisim']:.2f}")
                st.metric("F/K", f"{data2['fk']:.2f}")
                st.metric("ROE", f"%{data2['roe']:.1f}")
                st.metric("RSI", f"{data2['rsi']:.1f}")

            st.markdown("---")
            st.info(f"🤖 **AI Hakem Yorumu:**\n\n{ai_analiz('DUELLO', data1, data2)}")
            
        else:
            # --- TEKLİ ANALİZ EKRANI ---
            st.subheader(f"📊 {data1['ad']} Dashboard")
            
            # Kartlar (4 Kolon)
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Anlık Fiyat", f"{data1['fiyat']} ₺", f"%{data1['degisim']:.2f}")
            k2.metric("F/K Oranı", f"{data1['fk']:.2f}")
            k3.metric("Özsermaye Karlılığı (ROE)", f"%{data1['roe']:.1f}")
            
            rsi_val = data1['rsi']
            rsi_color = "inverse" if rsi_val > 70 else ("off" if rsi_val < 30 else "normal")
            k4.metric("RSI İndikatörü", f"{rsi_val:.1f}", delta_color=rsi_color)
            
            st.markdown("---")
            
            # Grafik ve AI Yan Yana
            g1, g2 = st.columns([2, 1]) # Grafik geniş, Yorum dar
            
            with g1:
                st.markdown("#### 📈 Fiyat Grafiği")
                fig = go.Figure()
                fig.add_trace(go.Candlestick(x=data1['hist'].index, open=data1['hist']['Open'], 
                                             high=data1['hist']['High'], low=data1['hist']['Low'], 
                                             close=data1['hist']['Close'], name=data1['ad']))
                fig.update_layout(height=400, template="plotly_dark", margin=dict(l=0, r=0, t=30, b=0))
                st.plotly_chart(fig, use_container_width=True)
                
            with g2:
                st.markdown("#### 🧠 Analist Görüşü")
                yorum = ai_analiz('TEK', data1)
                st.success(yorum)
