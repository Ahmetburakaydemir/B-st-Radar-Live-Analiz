import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from groq import Groq
import pandas as pd

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="BIST Radar: Düello",
    page_icon="🥊",
    layout="wide"
)

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

# --- 3. YARDIMCI FONKSİYONLAR (İŞÇİ ROBOTLAR) ---
def rsi_hesapla(data, window=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def veri_getir(sembol):
    """Verilen sembol için tüm verileri çeker ve paketler"""
    try:
        hisse = yf.Ticker(sembol)
        bilgi = hisse.info
        hist = hisse.history(period="1y")
        
        if 'currentPrice' not in bilgi:
            return None
            
        # Temel Veriler
        data = {
            'fiyat': bilgi.get('currentPrice'),
            'fk': bilgi.get('trailingPE', 0),
            'pd_dd': bilgi.get('priceToBook', 0),
            'roe': bilgi.get('returnOnEquity', 0) * 100,
            'buyume': bilgi.get('revenueGrowth', 0) * 100,
            'borc': bilgi.get('debtToEquity', 0) / 100,
            'ad': bilgi.get('longName', sembol),
            'hist': hist
        }
        
        # Teknik Hesaplamalar
        data['hist']['RSI'] = rsi_hesapla(data['hist'])
        data['rsi'] = data['hist']['RSI'].iloc[-1]
        
        onceki_kapanis = data['hist']['Close'].iloc[-2]
        data['degisim'] = ((data['fiyat'] - onceki_kapanis) / onceki_kapanis) * 100
        
        return data
    except Exception:
        return None

# --- AI ANALİZ FONKSİYONU (TEKLİ ve DÜELLO) ---
@st.cache_data(ttl=0, show_spinner=False)
def ai_analiz(mod, veri1, veri2=None):
    """
    mod: 'TEK' veya 'DUELLO'
    veri1: Ana hisse verileri
    veri2: Rakip hisse verileri (Opsiyonel)
    """
    try:
        if mod == 'TEK':
            prompt = f"""
            Sen uzman bir finansçısın. {veri1['ad']} hissesini analiz et.
            Veriler: Fiyat {veri1['fiyat']} TL, F/K {veri1['fk']:.2f}, PD/DD {veri1['pd_dd']:.2f}, 
            ROE %{veri1['roe']:.1f}, RSI {veri1['rsi']:.1f}.
            Kural: Türkçe konuş, yatırım tavsiyesi verme. Şirket sağlığını ve çarpanlarını yorumla.
            """
        else:
            prompt = f"""
            Sen uzman bir borsa stratejistisin. Şu iki şirketi "Yatırımcı Gözüyle" kıyasla:
            
            1. ŞİRKET: {veri1['ad']}
            - F/K: {veri1['fk']:.2f} | PD/DD: {veri1['pd_dd']:.2f} | ROE: %{veri1['roe']:.1f} | RSI: {veri1['rsi']:.1f}
            
            2. ŞİRKET: {veri2['ad']}
            - F/K: {veri2['fk']:.2f} | PD/DD: {veri2['pd_dd']:.2f} | ROE: %{veri2['roe']:.1f} | RSI: {veri2['rsi']:.1f}
            
            GÖREV:
            - Bu iki şirketi birbiriyle kıyasla.
            - "Hangisi daha ucuz?", "Hangisi daha karlı (ROE)?", "Hangisinin tekniği (RSI) daha iyi?" sorularına cevap ver.
            - Sonuç olarak bir kazanan ilan etme ama hangisinin hangi konuda (Büyüme mi Değer mi) önde olduğunu söyle.
            - %100 Türkçe ve akıcı ol. Yatırım tavsiyesi verme.
            """
            
        chat = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.5
        )
        return chat.choices[0].message.content
    except Exception as e:
        return f"AI Hatası: {str(e)}"

# --- 4. ARAYÜZ ---
st.title("🥊 BIST Radar: Hisse Düellosu")
st.markdown("---")

# Yan Menü
st.sidebar.header("🔍 Hisse Seçimi")

# Ana Hisse Seçimi
list_secenekler = [f"{k} - {v}" for k, v in BIST_SIRKETLERI.items()]
secim1 = st.sidebar.selectbox("1. Hisse (Ana)", list_secenekler, index=0)
kod1 = secim1.split(" - ")[0] + ".IS"

# Rakip Hisse Seçimi (Checkbox ile aktif olur)
kiyaslama_modu = st.sidebar.checkbox("Rakip Ekle (Kıyaslama Yap)")
kod2 = None

if kiyaslama_modu:
    secim2 = st.sidebar.selectbox("2. Hisse (Rakip)", list_secenekler, index=1)
    kod2 = secim2.split(" - ")[0] + ".IS"
    analyze_btn_text = "DÜELLOYU BAŞLAT ⚔️"
else:
    analyze_btn_text = "ANALİZ ET ✨"

analyze_button = st.sidebar.button(analyze_btn_text)

# --- ANA PROGRAM ---
if analyze_button:
    with st.spinner('Veriler toplanıyor ve AI hakem hazırlanıyor...'):
        
        # 1. Ana Hisseyi Çek
        data1 = veri_getir(kod1)
        if not data1:
            st.error("Ana hisse verisi çekilemedi.")
            st.stop()

        # 2. Mod Kontrolü
        if kiyaslama_modu and kod2:
            # DÜELLO MODU
            if kod1 == kod2:
                st.warning("Aynı hisseyi kıyaslayamazsın! Rakibi değiştir.")
                st.stop()
                
            data2 = veri_getir(kod2)
            if not data2:
                st.error("Rakip hisse verisi çekilemedi.")
                st.stop()
            
            # --- GÖRSELLEŞTİRME (YAN YANA) ---
            st.subheader(f"⚔️ KARŞILAŞTIRMA: {data1['ad']} vs {data2['ad']}")
            
            col_a, col_b = st.columns(2)
            
            # Sol Köşe (Ana Hisse)
            with col_a:
                st.info(f"🔹 {data1['ad']}")
                st.metric("Fiyat", f"{data1['fiyat']} ₺", f"%{data1['degisim']:.2f}")
                st.metric("F/K (Değerleme)", f"{data1['fk']:.2f}")
                st.metric("ROE (Karlılık)", f"%{data1['roe']:.1f}")
                st.metric("RSI (Teknik)", f"{data1['rsi']:.1f}")
            
            # Sağ Köşe (Rakip)
            with col_b:
                st.error(f"🔸 {data2['ad']}")
                st.metric("Fiyat", f"{data2['fiyat']} ₺", f"%{data2['degisim']:.2f}")
                st.metric("F/K (Değerleme)", f"{data2['fk']:.2f}", delta_color="inverse")
                st.metric("ROE (Karlılık)", f"%{data2['roe']:.1f}")
                st.metric("RSI (Teknik)", f"{data2['rsi']:.1f}")
            
            st.markdown("---")
            st.subheader("🤖 AI Stratejist Karşılaştırması")
            
            rapor = ai_analiz("DUELLO", data1, data2)
            st.success(rapor)
            
        else:
            # TEKLİ MOD (Eski versiyonun aynısı)
            st.subheader(f"🏢 {data1['ad']} Analizi")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Fiyat", f"{data1['fiyat']} ₺", f"%{data1['degisim']:.2f}")
            c2.metric("F/K", f"{data1['fk']:.2f}")
            c3.metric("ROE", f"%{data1['roe']:.1f}")
            c4.metric("RSI", f"{data1['rsi']:.1f}")
            
            st.markdown("---")
            st.subheader("📝 AI Yorumu")
            rapor = ai_analiz("TEK", data1)
            st.info(rapor)
            
            # Grafik (Sadece teklide grafik çizelim, sayfa karışmasın)
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=data1['hist'].index, open=data1['hist']['Open'], 
                                         high=data1['hist']['High'], low=data1['hist']['Low'], 
                                         close=data1['hist']['Close'], name=data1['ad']))
            fig.update_layout(height=400, template="plotly_dark", title=f"{data1['ad']} Grafiği")
            st.plotly_chart(fig, use_container_width=True)

