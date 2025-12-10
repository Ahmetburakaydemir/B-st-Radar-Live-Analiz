import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import google.generativeai as genai

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="BIST Radar AI",
    page_icon="🧠",
    layout="wide"
)

# --- 1. API KURULUMU (KASADAN ANAHTARI AL) ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except Exception:
    st.error("⚠️ API Anahtarı bulunamadı! Streamlit Secrets ayarlarını kontrol et.")
    st.stop()

# --- 2. TEKNİK FONKSİYONLAR ---
def rsi_hesapla(data, window=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def yapay_zeka_yorumu_al(sembol, fiyat, fk, pd_dd, rsi, degisim):
    """Google Gemini'ye verileri gönderip yorum alır"""
    model = genai.GenerativeModel('gemini-pro')
 # Hızlı ve ekonomik model
    
    prompt = f"""
    Sen kıdemli bir Borsa İstanbul analistisin. Aşağıdaki verilere göre {sembol} hissesi için 
    kısa, vurucu ve profesyonel bir yatırımcı notu yaz. 
    Yatırım tavsiyesi verme (AL/SAT deme), sadece risk ve fırsatları vurgula.
    Maddeler halinde yazma, akıcı bir paragraf olsun.

    VERİLER:
    - Hisse: {sembol}
    - Fiyat: {fiyat} TL
    - Günlük Değişim: %{degisim:.2f}
    - F/K Oranı: {fk} (Sektör ortalaması 10 kabul et)
    - PD/DD Oranı: {pd_dd}
    - RSI (14): {rsi:.1f} (30 altı aşırı satım, 70 üstü aşırı alım)
    """
    
    response = model.generate_content(prompt)
    return response.text

# --- 3. ARAYÜZ (FRONTEND) ---
st.title("🧠 BIST Radar: Yapay Zeka Destekli Analiz")
st.markdown("---")

st.sidebar.header("🔍 Hisse Seçimi")
sembol = st.sidebar.text_input("Hisse Kodu", value="THYAO").upper()
if not sembol.endswith(".IS"): sembol += ".IS"

analyze_button = st.sidebar.button("Analiz Et (AI) ✨")

if analyze_button:
    try:
        with st.spinner(f'{sembol} taranıyor ve Yapay Zeka raporu hazırlanıyor...'):
            # Veri Çekme
            hisse = yf.Ticker(sembol)
            bilgi = hisse.info
            hist = hisse.history(period="1y")
            
            if 'currentPrice' not in bilgi:
                st.error("Veri çekilemedi. Hisse kodunu kontrol et.")
            else:
                # Hesaplamalar
                guncel_fiyat = bilgi.get('currentPrice')
                fk = bilgi.get('trailingPE', 0)
                pd_dd = bilgi.get('priceToBook', 0)
                hist['RSI'] = rsi_hesapla(hist)
                son_rsi = hist['RSI'].iloc[-1]
                
                # Günlük değişim yüzdesi
                onceki_kapanis = hist['Close'].iloc[-2]
                degisim = ((guncel_fiyat - onceki_kapanis) / onceki_kapanis) * 100

                # --- METRİKLER ---
                st.subheader(f"🏢 {bilgi.get('longName', sembol)}")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Fiyat", f"{guncel_fiyat} ₺", f"%{degisim:.2f}")
                c2.metric("F/K", f"{fk:.2f}")
                c3.metric("PD/DD", f"{pd_dd:.2f}")
                c4.metric("RSI", f"{son_rsi:.1f}")
                
                st.markdown("---")

                # --- YAPAY ZEKA RAPORU (BURASI YENİ!) ---
                st.subheader("🤖 AI Analist Görüşü")
                
                # Gemini'ye Bağlanıyoruz
                ai_raporu = yapay_zeka_yorumu_al(sembol, guncel_fiyat, fk, pd_dd, son_rsi, degisim)
                
                # Raporu havalı bir kutuda gösterelim
                st.info(ai_raporu)
                
                st.markdown("---")

                # --- GRAFİK ---
                st.subheader("Teknik Görünüm")
                fig = go.Figure()
                fig.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'],
                                             low=hist['Low'], close=hist['Close'], name='Fiyat'))
                fig.update_layout(height=400, template="plotly_dark", title=f"{sembol} Mum Grafiği")
                st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Bir hata oluştu: {e}")
