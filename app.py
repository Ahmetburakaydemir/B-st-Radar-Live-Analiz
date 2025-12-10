import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go # Yeni Görselleştirme Kütüphanemiz

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="BIST Radar PRO",
    page_icon="📡",
    layout="wide"
)

# --- FONKSİYONLAR ---
def rsi_hesapla(data, window=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# --- BAŞLIK ---
st.title("📡 BIST Radar: Profesyonel Analiz")
st.markdown("---")

# --- YAN MENÜ ---
st.sidebar.header("🔍 Hisse Arama")
sembol = st.sidebar.text_input("Hisse Kodu", value="THYAO").upper()

if not sembol.endswith(".IS"):
    arama_kodu = sembol + ".IS"
else:
    arama_kodu = sembol

periyot = st.sidebar.selectbox("Zaman Aralığı", ["3mo", "6mo", "1y", "2y"], index=1)
analyze_button = st.sidebar.button("Analiz Et 🚀")

# --- ANA PROGRAM ---
if analyze_button:
    try:
        with st.spinner('Veriler Bloomberg terminali kalitesinde işleniyor...'):
            # Veri Çekme
            hisse = yf.Ticker(arama_kodu)
            bilgi = hisse.info
            gecmis_veri = hisse.history(period=periyot)
            
            if 'currentPrice' not in bilgi:
                st.error(f"❌ Hata: '{sembol}' verisi çekilemedi.")
            else:
                # RSI Hesapla
                gecmis_veri['RSI'] = rsi_hesapla(gecmis_veri)
                son_rsi = gecmis_veri['RSI'].iloc[-1]
                
                # --- ÜST BİLGİ KARTLARI ---
                st.subheader(f"🏢 {bilgi.get('longName', sembol)}")
                col1, col2, col3, col4 = st.columns(4)
                
                col1.metric("Fiyat", f"{bilgi.get('currentPrice')} ₺")
                col2.metric("F/K", f"{bilgi.get('trailingPE', 0):.2f}")
                col3.metric("PD/DD", f"{bilgi.get('priceToBook', 0):.2f}")
                
                rsi_renk = "inverse" if son_rsi > 70 else ("off" if son_rsi < 30 else "normal")
                col4.metric("RSI (Momentum)", f"{son_rsi:.1f}", delta_color=rsi_renk)
                
                st.markdown("---")

                # --- PROFESYONEL GRAFİK (MUM GRAFİĞİ) ---
                st.subheader(f"📈 {sembol} Fiyat Hareketleri (Candlestick)")
                
                # Plotly ile Mum Grafiği Çizimi
                fig = go.Figure()
                
                # Mum Çubukları (Kırmızı/Yeşil)
                fig.add_trace(go.Candlestick(
                    x=gecmis_veri.index,
                    open=gecmis_veri['Open'],
                    high=gecmis_veri['High'],
                    low=gecmis_veri['Low'],
                    close=gecmis_veri['Close'],
                    name='Fiyat'
                ))
                
                # Grafiği Güzelleştirme
                fig.update_layout(
                    height=500,
                    title=f'{sembol} Teknik Analiz Grafiği',
                    yaxis_title='Fiyat (TL)',
                    xaxis_rangeslider_visible=False, # Alttaki kaydırma çubuğunu gizle
                    template="plotly_dark" # Karanlık mod (Daha havalı)
                )
                
                # Grafiği Ekrana Bas
                st.plotly_chart(fig, use_container_width=True)

                # --- RSI GRAFİĞİ (ALTTA) ---
                st.info("💡 İPUCU: Grafiğin üzerine gelerek zoom yapabilir, değerleri görebilirsin.")
                
                # RSI için basit çizgi grafik devam etsin
                st.subheader("RSI Göstergesi")
                st.line_chart(gecmis_veri['RSI'])

    except Exception as e:

        st.error(f"Beklenmedik bir hata: {e}")
