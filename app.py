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

# --- 2. CSS: PRESTİJLİ VE KARARLI GÖRÜNÜM ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    .stApp {
        background-color: #F8F9FA;
        color: #111;
        font-family: 'Inter', sans-serif;
    }

    /* SIDEBAR (BORDO & BEYAZ) - Mobil Uyumlu */
    section[data-testid="stSidebar"] { background-color: #8B0000 !important; }
    section[data-testid="stSidebar"] * { color: #FFFFFF !important; }
    
    /* Selectbox ve Buton İyileştirmeleri */
    div[data-testid="stSidebar"] .stSelectbox > div > div {
        background-color: rgba(255, 255, 255, 0.15) !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        color: white !important;
    }
    div[data-testid="stSidebar"] .stButton > button {
        background-color: white !important;
        color: #8B0000 !important;
        font-weight: 800 !important;
        border: none;
        padding: 12px;
        transition: transform 0.2s;
    }
    div[data-testid="stSidebar"] .stButton > button:hover {
        transform: scale(1.02);
        background-color: #f0f0f0 !important;
    }

    /* KART TASARIMLARI */
    .hero-box {
        text-align: center; padding: 30px; margin-bottom: 20px;
        background: white; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.03);
    }
    .company-name { font-size: 38px; font-weight: 800; color: #111; margin: 0; }
    .company-sector { font-size: 14px; color: #666; letter-spacing: 2px; text-transform: uppercase; }
    
    /* Metrik Kutuları */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E5E5E5 !important;
        border-radius: 12px !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.02) !important;
        padding: 15px !important;
    }
    div[data-testid="stMetric"] label { color: #777 !important; font-size: 13px !important; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #111 !important; font-size: 24px !important; }

    /* F-RAY Skor Kartı */
    .score-card {
        background: #1D1D1F; color: white; padding: 25px; border-radius: 16px;
        text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.15);
    }
    
    /* AI Kutusu */
    .ai-card {
        background: #fff; border-left: 5px solid #111; padding: 25px;
        border-radius: 8px; box-shadow: 0 5px 20px rgba(0,0,0,0.05);
        color: #333; line-height: 1.6;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. LİSTE (GÜVENİLİR HİSSELER) ---
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
    "EKGYO": "EMLAK KONUT", "MGROS": "MİGROS", "DOAS": "DOĞUŞ OTOMOTİV",
    "ALARK": "ALARKO", "TAVHL": "TAV HAVALİMANLARI", "GUBRF": "GÜBRE FABRİKALARI"
}

# --- 4. API ---
try:
    api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=api_key)
except: st.error("API Key Hatası"); st.stop()

# --- 5. GÜÇLENDİRİLMİŞ VERİ MOTORU (ZIRHLI) ---
def rsi_hesapla(data, window=14):
    try:
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    except: return 50 # Hesaplayamazsa nötr dön

def veri_getir(sembol):
    """
    Bu fonksiyon veriyi bulmak için sonuna kadar savaşır.
    Bulamazsa '0' veya '-' döner ama asla çökmez.
    """
    try:
        hisse = yf.Ticker(sembol)
        
        # 1. ADIM: GEÇMİŞ VERİ (GRAFİK İÇİN ŞART)
        hist = hisse.history(period="1y")
        
        if hist.empty:
            return None # Grafik bile yoksa bu hissede iş yoktur.

        # Fiyatı Info yerine History'den al (Çok daha güvenilir)
        guncel_fiyat = hist['Close'].iloc[-1]
        
        # 2. ADIM: TEMEL VERİLER (YEDEK MEKANIZMALI)
        try:
            bilgi = hisse.info
        except:
            bilgi = {} # Hata verirse boş sözlükle devam et

        # Veriyi güvenli çekme fonksiyonu
        def guvenli(key_list, default=0):
            # Birden fazla anahtar dene (Yahoo bazen key değiştirir)
            for key in key_list:
                val = bilgi.get(key)
                if val is not None:
                    return val
            return default

        # F/K Oranı (Trailing veya Forward dene)
        fk = guvenli(['trailingPE', 'forwardPE'])
        
        # Eğer F/K hala 0 ise ve EPS varsa manuel hesapla
        if fk == 0:
            eps = guvenli(['trailingEps', 'forwardEps'])
            if eps != 0:
                fk = guncel_fiyat / eps

        # Diğer Oranlar
        pd_dd = guvenli(['priceToBook'])
        roe = guvenli(['returnOnEquity']) * 100
        buyume = guvenli(['revenueGrowth', 'earningsGrowth']) * 100
        
        # Metinler
        ad = bilgi.get('longName', sembol)
        sektor = bilgi.get('sector', 'BIST Ana Pazar')
        ozet = bilgi.get('longBusinessSummary', 'Şirket verisi hazırlanıyor...')

        # 3. ADIM: TEKNİK
        hist['RSI'] = rsi_hesapla(hist)
        son_rsi = hist['RSI'].iloc[-1]
        
        onceki_kapanis = hist['Close'].iloc[-2]
        degisim = ((guncel_fiyat - onceki_kapanis) / onceki_kapanis) * 100

        # 4. ADIM: PUANLAMA (Eksik veriye toleranslı)
        puan = 0
        
        # ROE Puanı (Veri yoksa nötr puan ver)
        if roe > 30: puan += 30
        elif roe > 10: puan += 15
        elif roe == 0: puan += 10 # Veri yoksa cezalandırma
        
        # F/K Puanı
        if 0 < fk < 12: puan += 30
        elif 12 <= fk < 25: puan += 15
        elif fk == 0: puan += 10 # Veri yoksa nötr
        
        # RSI Puanı
        if 30 <= son_rsi <= 70: puan += 20
        
        # Büyüme Puanı
        if buyume > 20: puan += 20
        elif buyume == 0: puan += 10
        
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
        # Prompt'u basitleştirdik, hata payını azalttık
        prompt = f"""
        Rol: Finans Uzmanı. Dil: Türkçe.
        Hisse: {veri['ad']}
        Veriler: Fiyat {veri['fiyat']:.2f}, F/K {veri['fk']:.2f}, ROE %{veri['roe']:.1f}, Puan {veri['puan']}.
        Özet: {veri['ozet'][:150]}...
        
        GÖREV:
        1. Şirket ne iş yapar? (1 Cümle)
        2. Bu veriler (F/K, ROE) olumlu mu olumsuz mu?
        3. Risk ve Fırsat nedir?
        """
        chat = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.1
        )
        return metni_temizle(chat.choices[0].message.content)
    except: return "Analiz şu an oluşturulamıyor. Lütfen grafikleri inceleyin."

# --- 6. ARAYÜZ (GÜVENLİ) ---
# Sidebar
st.sidebar.markdown("### 🎯 ODAK")
secim1 = st.sidebar.selectbox("Hisse Seçiniz", [f"{k} - {v}" for k, v in BIST_SIRKETLERI.items()])
kod1 = secim1.split(" - ")[0] + ".IS"
analyze_btn = st.sidebar.button("ANALİZ ET")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📚 AKADEMİ")
with st.sidebar.expander("Sözlük & Bilgi"):
    st.markdown("""
    * **F/K:** Kaç yılda amorti eder? (0-12: Ucuz).
    * **ROE:** Kararlılık. (%20+ İyidir).
    * **RSI:** Trend gücü. (30: Dip, 70: Zirve).
    """)
st.sidebar.info("⚠️ Veriler Yahoo Finance kaynaklıdır. Gecikmeli olabilir.")

# Main
if analyze_btn:
    with st.spinner('ODAK motoru verileri işliyor...'):
        data = veri_getir(kod1)
        
        if data:
            # 1. HERO SECTION
            st.markdown(f"""
            <div class='hero-box'>
                <div class='company-sector'>{data['sektor']}</div>
                <h1 class='company-name'>{data['ad']}</h1>
                <div style='font-size:32px; font-weight:700; margin-top:10px;'>
                    {data['fiyat']:.2f} ₺ 
                    <span style='font-size:18px; color:{'#27ae60' if data['degisim']>0 else '#c0392b'};'>
                        %{data['degisim']:.2f}
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # 2. METRİKLER (Veri yoksa '-' göster)
            c1, c2 = st.columns([1, 2])
            
            with c1:
                renk = "#27ae60" if data['puan'] >= 80 else ("#f1c40f" if data['puan'] >= 50 else "#e74c3c")
                durum = "MÜKEMMEL" if data['puan'] >= 80 else ("İYİ / ORTA" if data['puan'] >= 50 else "RİSKLİ")
                
                st.markdown(f"""
                <div class='score-card'>
                    <div style='font-size:12px; opacity:0.7;'>SAĞLIK PUANI</div>
                    <div style='font-size:64px; font-weight:800;'>{data['puan']}</div>
                    <div style='color:{renk}; font-weight:bold;'>{durum}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with c2:
                # Verileri formatla, 0 ise '-' yaz
                fk_fmt = f"{data['fk']:.2f}" if data['fk'] > 0 else "-"
                roe_fmt = f"%{data['roe']:.1f}" if data['roe'] != 0 else "-"
                buyume_fmt = f"%{data['buyume']:.1f}" if data['buyume'] != 0 else "-"
                
                m1, m2 = st.columns(2)
                m1.metric("F/K Oranı", fk_fmt)
                m1.metric("ROE (Karlılık)", roe_fmt)
                m2.metric("Büyüme", buyume_fmt)
                m2.metric("RSI (Teknik)", f"{data['rsi']:.1f}")

            # 3. GRAFİK VE AI
            st.markdown("---")
            st.markdown("### 📉 Teknik Analiz")
            fig = go.Figure(data=[go.Candlestick(x=data['hist'].index, open=data['hist']['Open'], 
                            high=data['hist']['High'], low=data['hist']['Low'], close=data['hist']['Close'])])
            fig.update_layout(height=400, template="plotly_white", margin=dict(t=0,b=0,l=0,r=0))
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("### 🧠 ODAK Görüşü")
            yorum = ai_analiz(data)
            st.markdown(f"<div class='ai-card'>{yorum}</div>", unsafe_allow_html=True)
            
        else:
            st.warning("⚠️ Bu hisse için şu an veri çekilemiyor. (Yahoo sunucularından kaynaklı anlık bir durum olabilir). Lütfen GARAN veya THYAO gibi ana hisseleri deneyin.")
else:
    st.markdown("<br><br><h1 style='text-align:center;'>🎯 ODAK</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#666;'>Analiz için sol menüden hisse seçin.</p>", unsafe_allow_html=True)
