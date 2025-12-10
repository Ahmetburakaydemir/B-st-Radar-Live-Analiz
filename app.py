import streamlit as st
import google.generativeai as genai

st.title("🛠️ API Teşhis Ekranı")

# 1. Anahtarı Al
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    st.success("✅ API Anahtarı Kasadan Başarıyla Alındı.")
except Exception as e:
    st.error(f"❌ Anahtar Hatası: {e}")
    st.stop()

# 2. Modelleri Listele
st.write("Google Sunucularına Bağlanılıyor...")

try:
    st.subheader("Kullanılabilir Modeller Listesi:")
    
    # Google'a soruyoruz: Elinde ne var?
    modeller = genai.list_models()
    
    bulundu = False
    for m in modeller:
        # Sadece metin üretebilen modelleri göster
        if 'generateContent' in m.supported_generation_methods:
            st.code(f"Model Adı: {m.name}")
            bulundu = True
            
    if not bulundu:
        st.warning("⚠️ Hiçbir model bulunamadı. API Key yetkilerini kontrol et.")

except Exception as e:
    st.error(f"🚨 Bağlantı Hatası: {e}")
    st.info("İpucu: Eğer 'PermissionDenied' hatası alıyorsan, API Key geçersizdir.")
