import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from groq import Groq

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="BIST Radar AI",
    page_icon="🎓",
    layout="wide"
)

# --- 1. API KURULUMU (GROQ) ---
try:
    api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=api_key)
except Exception:
    st.error("⚠️ API Anahtarı hatası! Streamlit Secrets kısmını kontrol et.")
    st.stop()

# --- 2. TEKNİK FONKSİYONLAR ---
def rsi_hesapla(data, window=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# Cache ayarı (Hafızayı temizleyelim ki yeni prompt devreye girsin)
@st.cache_data(ttl=0, show_spinner=False)
def yapay_zeka_yorumu_al(sembol, fiyat, fk, pd_dd, rsi, degisim):
    """Groq (Llama 3.3) - %100 TÜRKÇE MENTOR MODU"""
    try:
        # --- GURU DOKUNUŞU: SIKI YÖNETİM PROMPT ---
        prompt = f"""
        Rolün: Sen Borsa İstanbul konusunda uzman, Türkçe'yi mükemmel ve akıcı kullanan, sabırlı bir finans öğretmenisin.
        Görev: Aşağıdaki verilere göre {sembol} hissesini analiz et.

        VERİLER:
        - Hisse: {sembol}
        - Fiyat: {fiyat} TL
        - Günlük Değişim: %{degisim:.2f}
        - F/K Oranı: {fk}
        - PD/DD Oranı: {pd_dd}
        - RSI: {rsi:.1f}

        ÇOK ÖNEMLİ KURALLAR (BUNLARA KESİN UY):
        1. DİL: Sadece ve sadece TÜRKÇE yaz. Asla İngilizce kelime (approximately, slightly, doing vs.) kullanma.
        2. KARAKTER: Asla Çince, Japonca veya bozuk karakter kullanma.
        3. ÜSLUP: Robotik çeviri gibi değil, doğal bir İstanbul Türkçesi ile konuş. Akıcı ve anlaşılır ol.
        4. YASAL: Asla "Yatırım Tavsiyesidir" deme.

        ANALİZ FORMATI:
        
        1. 📊 GENEL DURUM:
           Hissenin bugünkü hareketi ne anlatıyor? (Kısa özet)

        2. 💡 YATIRIMCI İÇİN FİNANSAL OKURYAZARLIK:
           Bu F/K ve PD/DD değerleri ne anlama geliyor?
           Örneğin: "F/K oranının {fk} olması, şirketin kendini amorti etme süresinin makul olduğunu gösterir..." gibi öğretici konuş.
           Rakamları boğma, mantığını anlat.

        3. ⚖️ RİSK VE FIRSAT PENCERESİ:
           RSI değerine ({rsi:.1f}) bakarak hisse pahalı mı ucuz mu? Yatırımcı neye dikkat etmeli?
        """
        
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile", 
            temperature=0.5, # Yaratıcılığı biraz kıstık ki saçmalamasın, daha tutarlı olsun.
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"HATA: {str(e)}"

# --- 3. ARAYÜZ ---
st.title("🎓 BIST Radar: Finansal Mentor")
st.markdown("---")

st.sidebar.header("🔍 Hisse Seçimi")
sembol = st.sidebar.text_input("Hisse Kodu", value="THYAO").upper()
if not sembol.endswith(".IS"): sembol += ".IS"

st.sidebar.info("Mod: %100 Türkçe Mentor 🇹🇷")
analyze_button = st.sidebar.button("Analiz Et (AI) ✨")

if analyze_button:
    try:
        with st.spinner(f'{sembol} finansal karnesi çıkarılıyor...'):
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
                st.subheader("📝 Yapay Zeka Yorumu")
                
                ai_raporu = yapay_zeka_yorumu_al(sembol, guncel_fiyat, fk, pd_dd, son_rsi, degisim)
                
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
