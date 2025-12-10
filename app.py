import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="BIST Radar PRO",
    page_icon="📡",
    layout="wide"
)

# --- FONKSİYONLAR ---
def rsi_hesapla(data, window=14):
    """Pandas ile RSI (Göreceli Güç Endeksi) hesaplar"""
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# --- BAŞLIK ---
st.title("📡 BIST Radar PRO: Teknik & Temel Analiz")
st.markdown("---")

# --- YAN MENÜ ---
st.sidebar.header("🔍 Hisse Arama")
sembol = st.sidebar.text_input("Hisse Kodu (Örn: ASELS, THYAO)", value="THYAO").upper()

if not sembol.endswith(".IS"):
    arama_kodu = sembol + ".IS"
else:
    arama_kodu = sembol

analyze_button = st.sidebar.button("Analiz Et 🚀")

st.sidebar.info("PRO Sürüm: Artık RSI ve Teknik Göstergeler devrede.")

# --- ANA PROGRAM ---
if analyze_button:
    try:
        with st.spinner(f'{sembol} verileri ve teknik indikatörler hesaplanıyor...'):
            # Veri Çekme (Son 1 Yıllık veri lazım teknik analiz için)
            hisse = yf.Ticker(arama_kodu)
            bilgi = hisse.info
            gecmis_veri = hisse.history(period="1y")
            
            if 'currentPrice' not in bilgi:
                st.error(f"❌ Hata: '{sembol}' verisi çekilemedi.")
            else:
                # --- HESAPLAMALAR ---
                # RSI Hesapla ve son veriye ekle
                gecmis_veri['RSI'] = rsi_hesapla(gecmis_veri)
                son_rsi = gecmis_veri['RSI'].iloc[-1]
                
                # --- 1. ÜST BİLGİ KARTLARI ---
                st.subheader(f"🏢 {bilgi.get('longName', sembol)}")
                
                col1, col2, col3, col4 = st.columns(4)
                fiyat = bilgi.get('currentPrice')
                fk = bilgi.get('trailingPE')
                pd_dd = bilgi.get('priceToBook')
                
                col1.metric("Fiyat", f"{fiyat} ₺")
                col2.metric("F/K", f"{fk:.2f}" if fk else "-")
                col3.metric("PD/DD", f"{pd_dd:.2f}" if pd_dd else "-")
                
                # RSI Rengi Ayarlama
                rsi_renk = "normal"
                if son_rsi > 70: rsi_renk = "inverse" # Kırmızı (Tehlike)
                if son_rsi < 30: rsi_renk = "off"     # Yeşilimsi (Fırsat) - Streamlit hilesi
                
                col4.metric("RSI (Teknik)", f"{son_rsi:.1f}", delta_color=rsi_renk)
                
                # --- 2. YAPAY ZEKA YORUMU (HİBRİT) ---
                st.markdown("---")
                st.subheader("🤖 Yapay Zeka Görüşü (Temel + Teknik)")
                
                c1, c2 = st.columns(2)
                
                with c1:
                    st.info("📊 **Temel Analiz (Şirket Durumu)**")
                    # F/K Yorumu
                    if fk:
                        if fk < 5: st.write("✅ F/K çok düşük. Şirket ucuz kalmış.")
                        elif fk > 20: st.write("⚠️ F/K yüksek. Geleceği fiyatlıyor olabilir.")
                        else: st.write("⚖️ F/K makul seviyelerde.")
                    # PD/DD Yorumu
                    if pd_dd and pd_dd < 1: st.write("✅ Defter değerinin altında işlem görüyor.")

                with c2:
                    st.warning("📈 **Teknik Analiz (Zamanlama)**")
                    # RSI Yorumu
                    if son_rsi > 70:
                        st.write(f"🔥 **RSI: {son_rsi:.0f} (AŞIRI ALIM)**")
                        st.write("Hisse çok hızlı yükselmiş, kar satışı gelebilir. Dikkatli ol.")
                    elif son_rsi < 30:
                        st.write(f"❄️ **RSI: {son_rsi:.0f} (AŞIRI SATIM)**")
                        st.write("Hisse çok düşmüş, tepki yükselişi gelebilir. Fırsat bölgesi.")
                    else:
                        st.write(f"↔️ **RSI: {son_rsi:.0f} (NÖTR)**")
                        st.write("Hisse dengeli seyrediyor. Aşırılık yok.")

                # --- 3. GRAFİKLER (FİYAT VE RSI) ---
                st.markdown("---")
                st.subheader("Grafik Analizi")
                
                # İki sekmeli yapı kuralım
                tab1, tab2 = st.tabs(["Fiyat Grafiği", "RSI Göstergesi"])
                
                with tab1:
                    st.line_chart(gecmis_veri['Close'])
                    
                with tab2:
                    # RSI Grafiğini Matplotlib ile çizelim (Limit çizgileri için)
                    fig, ax = plt.subplots(figsize=(10, 4))
                    ax.plot(gecmis_veri.index, gecmis_veri['RSI'], color='purple', label='RSI')
                    ax.axhline(70, color='red', linestyle='--', label='Aşırı Alım (70)')
                    ax.axhline(30, color='green', linestyle='--', label='Aşırı Satım (30)')
                    ax.set_title("RSI Momentum Grafiği")
                    ax.legend()
                    st.pyplot(fig)

    except Exception as e:
        st.error(f"Hata oluştu: {e}")
