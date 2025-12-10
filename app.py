import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="BIST Radar - AI Analiz",
    page_icon="📡",
    layout="wide"
)

# --- BAŞLIK VE YASAL UYARI ---
st.title("📡 BIST Radar: Temel Analiz Asistanı")
st.markdown("---")

st.error("⚠️ YASAL UYARI: Bu uygulama sadece eğitim ve veri görselleştirme amaçlıdır. "
         "Buradaki veriler ve yorumlar kesinlikle YATIRIM TAVSİYESİ DEĞİLDİR. "
         "Yatırım kararlarınızı SPK lisanslı uzmanlara danışarak alınız.")

# --- YAN MENÜ (INPUT) ---
st.sidebar.header("🔍 Hisse Arama")
st.sidebar.info("Analiz etmek istediğiniz hissenin kodunu girin.")

# Kullanıcıdan hisse kodunu al (Varsayılan: THYAO)
sembol = st.sidebar.text_input("Hisse Kodu (Örn: GARAN, EREGL)", value="THYAO").upper()

# Kullanıcı .IS yazmayı unutursa biz ekleyelim
if not sembol.endswith(".IS"):
    arama_kodu = sembol + ".IS"
else:
    arama_kodu = sembol

st.sidebar.markdown("---")
analyze_button = st.sidebar.button("Analiz Et 🚀")

# --- ANA PROGRAM ---
if analyze_button:
    try:
        with st.spinner(f'{sembol} verileri çekiliyor...'):
            # Veriyi Yahoo Finance'den çek
            hisse = yf.Ticker(arama_kodu)
            bilgi = hisse.info
            
            # Eğer veri boş gelirse hata ver
            if 'currentPrice' not in bilgi:
                st.error(f"❌ Hata: '{sembol}' kodlu hisse bulunamadı veya veri çekilemiyor.")
            else:
                # --- 1. GENEL BİLGİLER ---
                st.subheader(f"🏢 {bilgi.get('longName', sembol)}")
                st.write(f"**Sektör:** {bilgi.get('industry', 'Bilinmiyor')}")
                st.write(f"**Tanım:** {bilgi.get('longBusinessSummary', 'Açıklama yok.')[:200]}...")
                
                # --- 2. FİNANSAL METRİKLER (KARTLAR) ---
                col1, col2, col3, col4 = st.columns(4)
                
                fiyat = bilgi.get('currentPrice')
                fk = bilgi.get('trailingPE')
                pd_dd = bilgi.get('priceToBook')
                hacim = bilgi.get('volume')

                col1.metric("Anlık Fiyat", f"{fiyat} ₺")
                col2.metric("F/K Oranı", f"{fk:.2f}" if fk else "-")
                col3.metric("PD/DD Oranı", f"{pd_dd:.2f}" if pd_dd else "-")
                col4.metric("Hacim", f"{hacim:,}")
                
                st.markdown("---")

                # --- 3. GURU MANTIĞI (OTOMATİK YORUM) ---
                st.subheader("🤖 Yapay Zeka Görüşü")
                
                # F/K Yorumu
                if fk:
                    if fk < 5:
                        st.success(f"✅ **F/K ({fk:.2f}):** Şirket karına oranla ÇOK UCUZ fiyatlanıyor. (Fırsat olabilir)")
                    elif 5 <= fk < 15:
                        st.info(f"⚖️ **F/K ({fk:.2f}):** Makul seviyelerde işlem görüyor. (Nötr)")
                    else:
                        st.warning(f"⚠️ **F/K ({fk:.2f}):** Karlılığına göre fiyatı biraz YÜKSEK (Primli).")
                else:
                    st.error("❌ F/K oranı hesaplanamadı (Şirket zarar ediyor olabilir).")

                # PD/DD Yorumu
                if pd_dd:
                    if pd_dd < 1:
                        st.success(f"✅ **PD/DD ({pd_dd:.2f}):** Şirket defter değerinin ALTINDA işlem görüyor. (İskontolu)")
                    else:
                        st.info(f"ℹ️ **PD/DD ({pd_dd:.2f}):** Defter değerinin üzerinde fiyatlanıyor. (Piyasa beklentisi var)")

                st.markdown("---")

                # --- 4. GRAFİK (SON 6 AY) ---
                st.subheader("📈 Fiyat Grafiği (Son 6 Ay)")
                hist = hisse.history(period="6mo")
                st.line_chart(hist['Close'])

    except Exception as e:
        st.error(f"Bir hata oluştu: {e}")
