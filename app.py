import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from groq import Groq

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="BIST Radar AI", page_icon="⚡", layout="wide")

# --- 1. API KURULUMU ---
try:
    api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=api_key)
except Exception as e:
    st.error(f"⚠️ API Anahtarı sorunu: {e}")
    st.stop()

# --- 2. FONKSİYONLAR ---
def rsi_hesapla(data, window=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# Cache'i kapattık, hatayı görmek istiyoruz
@st.cache_data(ttl=0, show_spinner=False)
def yapay_zeka_yorumu_al(sembol, fiyat, fk, pd_dd, rsi, degisim):
    try:
        prompt = f"""
        Sen kıdemli bir borsa analistisin. {sembol} için kısa bir analiz yaz.
        Veriler: Fiyat {fiyat}, F/K {fk}, RSI {rsi}. 
        Yatırım tavsiyesi verme.
        """
        
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="mixtral-8x7b-32768",
        )
        return chat_completion.choices[0].message.content
        
    except Exception as e:
        # İŞTE BURASI: Hatayı gizlemek yerine geri döndürüyoruz!
        return f"HATA DETAYI: {str(e)}"

# --- 3. ARAYÜZ ---
st.title("⚡ BIST Radar: Teşhis Modu")
st.markdown("---")

st.sidebar.header("🔍 Hisse Seçimi")
sembol = st.sidebar.text_input("Hisse Kodu", value="THYAO").upper()
if not sembol.endswith(".IS"): sembol += ".IS"

analyze_button = st.sidebar.button("Analiz Et (AI) ✨")

if analyze_button:
    with st.spinner(f'{sembol} analiz ediliyor...'):
        try:
            hisse = yf.Ticker(sembol)
            bilgi = hisse.info
            hist = hisse.history(period="1y")
            
            if 'currentPrice' not in bilgi:
                st.error("Veri yok.")
            else:
                # Hesaplamalar
                guncel_fiyat = bilgi.get('currentPrice')
                fk = bilgi.get('trailingPE', 0)
                pd_dd = bilgi.get('priceToBook', 0)
                hist['RSI'] = rsi_hesapla(hist)
                son_rsi = hist['RSI'].iloc[-1]
                degisim = 0 # Basit tutalım şimdilik

                # Raporu Çağır
                st.subheader("🤖 AI Analist Görüşü")
                ai_raporu = yapay_zeka_yorumu_al(sembol, guncel_fiyat, fk, pd_dd, son_rsi, degisim)
                
                # Hatayı Kırmızı, Raporu Mavi Göster
                if "HATA DETAYI" in ai_raporu:
                    st.error(ai_raporu) # Kırmızı kutu
                else:
                    st.info(ai_raporu)  # Mavi kutu
                    
        except Exception as e:
            st.error(f"Genel Hata: {e}")
