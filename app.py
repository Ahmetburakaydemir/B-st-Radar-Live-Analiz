import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from groq import Groq

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="BIST Radar AI Pro",
    page_icon="💎",
    layout="wide"
)

# --- 1. SABİT VERİLER (AKILLI ARAMA İÇİN) ---
# Popüler BIST Şirketleri Listesi (Bunu zamanla genişletebilirsin)
BIST_SIRKETLERI = {
    "THYAO": "TÜRK HAVA YOLLARI",
    "GARAN": "GARANTİ BBVA",
    "ASELS": "ASELSAN",
    "EREGL": "EREĞLİ DEMİR ÇELİK",
    "SISE": "ŞİŞECAM",
    "KCHOL": "KOÇ HOLDİNG",
    "SAHOL": "SABANCI HOLDİNG",
    "AKBNK": "AKBANK",
    "YKBNK": "YAPI KREDİ BANKASI",
    "ISCTR": "İŞ BANKASI (C)",
    "BIMAS": "BİM MAĞAZALAR",
    "TUPRS": "TÜPRAŞ",
    "FROTO": "FORD OTOSAN",
    "TOASO": "TOFAŞ OTO",
    "PGSUS": "PEGASUS",
    "TCELL": "TURKCELL",
    "TTKOM": "TÜRK TELEKOM",
    "PETKM": "PETKİM",
    "SASA": "SASA POLYESTER",
    "HEKTS": "HEKTAŞ",
    "ENKAI": "ENKA İNŞAAT",
    "VESTL": "VESTEL",
    "ARCLK": "ARÇELİK",
    "ALARK": "ALARKO HOLDİNG",
    "EKGYO": "EMLAK KONUT GYO",
    "ODAS": "ODAŞ ELEKTRİK",
    "KOZAL": "KOZA ALTIN",
    "MGROS": "MİGROS",
    "ASTOR": "ASTOR ENERJİ",
    "KONTR": "KONTROLMATİK"
}

# --- 2. API KURULUMU (GROQ) ---
try:
    api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=api_key)
except Exception:
    st.error("⚠️ API Anahtarı hatası! Streamlit Secrets kısmını kontrol et.")
    st.stop()

# --- 3. TEKNİK FONKSİYONLAR ---
def rsi_hesapla(data, window=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# Cache ayarı
@st.cache_data(ttl=0, show_spinner=False)
def yapay_zeka_yorumu_al(sembol, ad, fiyat, fk, pd_dd, rsi, degisim, roe, borc_ozkaynak, buyume):
    """Groq (Llama 3.3) - DERİN ANALİZ MODU"""
    try:
        prompt = f"""
        Rolün: Sen Borsa İstanbul konusunda uzman, bilanço okumayı bilen kıdemli bir finansçısın.
        Görev: {ad} ({sembol}) hissesini hem teknik hem de TEMEL verilerle derinlemesine analiz et.

        YENİ EKLENEN KRİTİK VERİLER:
        - Özsermaye Karlılığı (ROE): %{roe} (Şirket sermayesini ne kadar verimli kullanıyor?)
        - Borç/Özkaynak Oranı: {borc_ozkaynak} (Riskli mi? 1'in altı genelde iyidir)
        - Gelir Büyümesi: %{buyume} (Şirket büyüyor mu?)

        DİĞER VERİLER:
        - Fiyat: {fiyat} TL (%{degisim:.2f} Değişim)
        - F/K: {fk}
        - PD/DD: {pd_dd}
        - RSI: {rsi:.1f}

        KURALLAR:
        1. Asla "Yatırım Tavsiyesidir" deme.
        2. %100 Türkçe ve akıcı konuş.
        3. Özellikle ROE ve Borçluluk durumunu yorumla (Bu bir bankacı bakış açısıdır).

        ANALİZ FORMATI:
        1. 🏢 ŞİRKET SAĞLIĞI (TEMEL ANALİZ):
           Büyüme, Borçluluk ve Karlılık (ROE) verilerine göre şirket sağlam mı?
           
        2. 📊 PİYASA ÇARPANLARI:
           F/K ve PD/DD oranları, şirketin karlılığına göre ucuz mu pahalı mı?

        3. ⚖️ TEKNİK GÖRÜNÜM VE RİSKLER:
           RSI ne diyor? Kısa vadeli riskler neler?
        """
        
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile", 
            temperature=0.5,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"HATA: {str(e)}"

# --- 4. ARAYÜZ ---
st.title("💎 BIST Radar Pro: Derin Analiz")
st.markdown("---")

st.sidebar.header("🔍 Akıllı Arama")

# 1. ÖZELLİK: SELECTBOX İLE ARAMA
# Sözlükten liste oluşturuyoruz: "THYAO - TÜRK HAVA YOLLARI" formatında
secenekler = [f"{kod} - {ad}" for kod, ad in BIST_SIRKETLERI.items()]
secilen = st.sidebar.selectbox("Hisse Seçiniz:", secenekler)

# Seçilen metinden sadece KODU alıyoruz (Örn: "THYAO" kısmını)
sembol = secilen.split(" - ")[0]
sirket_adi = secilen.split(" - ")[1]
arama_kodu = sembol + ".IS"

st.sidebar.info(f"Seçilen: {sirket_adi}")
st.sidebar.markdown("---")
analyze_button = st.sidebar.button("Detaylı Analiz Et (AI) 🚀")

if analyze_button:
    try:
        with st.spinner(f'{sirket_adi} bilançosu ve teknik verileri inceleniyor...'):
            hisse = yf.Ticker(arama_kodu)
            bilgi = hisse.info
            hist = hisse.history(period="1y")
            
            if 'currentPrice' not in bilgi:
                st.error("❌ Veri çekilemedi. Bağlantıyı kontrol et.")
            else:
                # --- VERİ TOPLAMA (YENİ METRİKLER) ---
                guncel_fiyat = bilgi.get('currentPrice')
                fk = bilgi.get('trailingPE', 0)
                pd_dd = bilgi.get('priceToBook', 0)
                
                # 2. ÖZELLİK: YENİ TEMEL ANALİZ VERİLERİ
                roe = bilgi.get('returnOnEquity', 0) * 100 # Yüzdeye çevir
                buyume = bilgi.get('revenueGrowth', 0) * 100 # Yüzdeye çevir
                borc_ozkaynak = bilgi.get('debtToEquity', 0) / 100 # Oran düzeltme
                
                hist['RSI'] = rsi_hesapla(hist)
                son_rsi = hist['RSI'].iloc[-1]
                onceki_kapanis = hist['Close'].iloc[-2]
                degisim = ((guncel_fiyat - onceki_kapanis) / onceki_kapanis) * 100

                # --- GÖRSELLEŞTİRME ---
                st.subheader(f"🏢 {sirket_adi} ({sembol}) Finansal Karnesi")
                
                # 1. Satır: Fiyat ve Çarpanlar
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Fiyat", f"{guncel_fiyat} ₺", f"%{degisim:.2f}")
                c2.metric("F/K", f"{fk:.2f}")
                c3.metric("PD/DD", f"{pd_dd:.2f}")
                rsi_renk = "inverse" if son_rsi > 70 else ("off" if son_rsi < 30 else "normal")
                c4.metric("RSI (Teknik)", f"{son_rsi:.1f}", delta_color=rsi_renk)
                
                # 2. Satır: ŞİRKET SAĞLIĞI (YENİ!)
                st.markdown("##### 🩺 Şirket Sağlık Göstergeleri")
                k1, k2, k3, k4 = st.columns(4)
                
                # ROE Göstergesi
                k1.metric("ROE (Özsermaye Karlılığı)", f"%{roe:.1f}", delta_color="normal" if roe > 30 else "off")
                
                # Büyüme Göstergesi
                k2.metric("Gelir Büyümesi (Yıllık)", f"%{buyume:.1f}", delta_color="normal" if buyume > 0 else "inverse")
                
                # Borçluluk (Düşük olması iyidir, o yüzden ters mantık)
                k3.metric("Borç/Özkaynak", f"{borc_ozkaynak:.2f}", delta_color="inverse" if borc_ozkaynak > 1.5 else "normal")
                
                k4.metric("Öneri", "AI Raporuna Bak 👇")

                st.markdown("---")

                # AI Raporu
                st.subheader("📝 Yapay Zeka Stratejist Yorumu")
                
                # Yeni verileri fonksiyona gönderiyoruz
                ai_raporu = yapay_zeka_yorumu_al(sembol, sirket_adi, guncel_fiyat, fk, pd_dd, son_rsi, degisim, roe, borc_ozkaynak, buyume)
                
                if "HATA" in ai_raporu:
                    st.error(ai_raporu)
                else:
                    st.info(ai_raporu)

                st.markdown("---")

                # Grafik
                st.subheader("Teknik Görünüm")
                fig = go.Figure()
                fig.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'],
                                             low=hist['Low'], close=hist['Close'], name='Fiyat'))
                fig.update_layout(height=400, template="plotly_dark", title=f"{sembol} Mum Grafiği")
                st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Beklenmedik bir hata: {e}")
