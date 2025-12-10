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

# --- 1. API KURULUMU ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except Exception:
    st.error("⚠️ API Anahtarı hatası! Secrets ayarlarını kontrol et.")
    st.stop()

# --- 2. TEKNİK FONKSİYONLAR ---
def rsi_hesapla(data, window=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def yapay_zeka_yorumu_al(sembol, fiyat, fk, pd_dd, rsi, degisim):
    """Google Gemini-1.5-Flash modeline verileri gönderip yorum alır"""
    try:
        # BURASI GÜNCELLENDİ: En yeni ve hızlı model
        model = genai.GenerativeModel('gemini-1.5-flash') 
        
        prompt = f"""
        Sen uzman bir borsa analistisin. Aşağıdaki verilere göre {sembol} hissesi için 
        yatırımcıya yönelik kısa, profesyonel ve akıcı bir analiz paragrafı yaz.
        Yatırım tavsiyesi (AL/SAT) verme, finansal okuryazarlık kapsamında yorumla.
        
        VERİLER:
        - Hisse Kodu: {sembol}
        - Anlık Fiyat: {fiyat} TL
        - Günlük Değişim: %{degisim:.2f}
        - F/K Oranı: {fk} 
        - PD/DD Oranı: {pd_dd}
        - RSI Değeri: {rsi:.1f}
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI Hatası: {e}. (Lütfen sayfayı yenilemeyi dene)."

# --- 3. ARAYÜZ ---
st.title("🧠 BIST Radar: Yapay Zeka Destekli Analiz")
st.markdown("---")

st.sidebar.header("🔍 Hisse Seçimi")
sembol = st.sidebar.text_input("Hisse Kodu", value="THYAO").upper()
if not sembol.endswith(".IS"): sembol += ".IS"

analyze_button = st.sidebar.button("Analiz Et (AI) ✨")

if analyze_button:
    try:
        with st.spinner(f'{sembol} taranıyor ve Yapay Zeka raporu hazırlanıyor...'):
            hisse = yf.Ticker(sembol)
            bilgi = hisse.info
            hist = hisse.history(period="1y")
            
            if 'currentPrice' not in bilgi:
                st.error("❌ Veri çekilemedi. Hisse kodunu kontrol et.")
            else:
                guncel_fiyat = bilgi.get('currentPrice')
                fk = bilgi.get('trailingPE', 0)
                pd_dd = bilgi.get('priceToBook', 0)
                hist['RSI'] = rsi_hesapla(hist)
                son_rsi = hist['RSI'].iloc[-1]
                onceki_kapanis = hist['Close'].iloc[-2]
                degisim = ((guncel_fiyat - onceki_kapanis) / onceki_kapanis) * 100

                # Metrikler
                st.subheader(f"🏢 {bilgi.get('longName', sembol)}")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Fiyat", f"{guncel_fiyat} ₺", f"%{degisim:.2f}")
                c2.metric("F/K", f"{fk:.2f}")
                c3.metric("PD/DD", f"{pd_dd:.2f}")
                rsi_renk = "inverse" if son_rsi > 70 else ("off" if son_rsi < 30 else "normal")
                c4.metric("RSI", f"{son_rsi:.1f}", delta_color=rsi_renk)
                
                st.markdown("---")

                # AI Raporu
                st.subheader("🤖 AI Analist Görüşü")
                ai_raporu = yapay_zeka_yorumu_al(sembol, guncel_fiyat, fk, pd_dd, son_rsi, degisim)
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
