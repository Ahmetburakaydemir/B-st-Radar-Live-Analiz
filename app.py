import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from groq import Groq
import re

# --- 1. SAYFA AYARLARI ---
st.set_page_config(
    page_title="ODAK | Master",
    page_icon="🎯",
    layout="wide"
)

# --- 2. CSS: FLIP CARD & PIANO WHITE ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    
    .stApp {
        background-color: #F8F9FA;
        color: #111;
        font-family: 'Inter', sans-serif;
    }

    /* SIDEBAR */
    section[data-testid="stSidebar"] { background-color: #8B0000 !important; }
    section[data-testid="stSidebar"] * { color: #FFFFFF !important; }
    div[data-testid="stSidebar"] .stButton > button {
        background-color: white !important; color: #8B0000 !important; font-weight: 800 !important; border: none;
    }

    /* --- FLIP CARD (DÖNEN KART) CSS SİHRİ --- */
    .flip-card {
        background-color: transparent;
        width: 100%;
        height: 140px; /* Kart Yüksekliği */
        perspective: 1000px; /* 3D derinlik etkisi */
        margin-bottom: 15px;
        cursor: pointer;
    }

    .flip-card-inner {
        position: relative;
        width: 100%;
        height: 100%;
        text-align: center;
        transition: transform 0.6s;
        transform-style: preserve-3d;
        box-shadow: 0 4px 8px 0 rgba(0,0,0,0.1);
        border-radius: 16px;
    }

    /* Tıklanınca (Javascript ile class eklenecek) veya üzerine gelince dönmesi için */
    .flip-card:active .flip-card-inner,
    .flip-card.flipped .flip-card-inner {
        transform: rotateY(180deg);
    }

    /* Ön ve Arka Yüz Ortak Ayarlar */
    .flip-card-front, .flip-card-back {
        position: absolute;
        width: 100%;
        height: 100%;
        -webkit-backface-visibility: hidden;
        backface-visibility: hidden;
        border-radius: 16px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        padding: 10px;
    }

    /* ÖN YÜZ (Veri) - Beyaz */
    .flip-card-front {
        background-color: #FFFFFF;
        color: black;
        border: 1px solid #E5E5E5;
    }

    /* ARKA YÜZ (Formül) - Siyah */
    .flip-card-back {
        background-color: #1D1D1F;
        color: white;
        transform: rotateY(180deg);
        border: 1px solid #333;
    }

    /* Kart İçi Yazı Stilleri */
    .card-title { font-size: 13px; color: #666; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }
    .card-value { font-size: 28px; font-weight: 800; color: #111; margin-top: 5px; }
    .card-formula { font-size: 14px; color: #FFD700; font-weight: bold; margin-bottom: 5px; }
    .card-desc { font-size: 12px; color: #ccc; line-height: 1.4; }

    /* DİĞER KUTULAR */
    .hero-box { background: white; padding: 30px; border-radius: 16px; text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.03); margin-bottom: 20px;}
    .company-name { font-size: 42px; font-weight: 800; color: #111; margin: 0; }
    .score-card { background: #1D1D1F; color: white; padding: 25px; border-radius: 16px; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.15); height: 140px; display: flex; flex-direction: column; justify-content: center;}
    .ai-card { background: #fff; border-left: 5px solid #111; padding: 25px; border-radius: 8px; box-shadow: 0 5px 20px rgba(0,0,0,0.05); color: #333; line-height: 1.6; }

    </style>
    
    <script>
    // Kartlara tıklanınca 'flipped' class'ını ekleyip çıkaran basit JS
    function flipCard(element) {
        element.classList.toggle("flipped");
    }
    </script>
    """, unsafe_allow_html=True)

# --- 3. LİSTE ---
BIST_SIRKETLERI = {
    "THYAO": "TÜRK HAVA YOLLARI", "GARAN": "GARANTİ BBVA", "ASELS": "ASELSAN",
    "EREGL": "EREĞLİ DEMİR ÇELİK", "TUPRS": "TÜPRAŞ", "SISE": "ŞİŞECAM",
    "AKBNK": "AKBANK", "YKBNK": "YAPI KREDİ", "ISCTR": "İŞ BANKASI (C)",
    "KCHOL": "KOÇ HOLDİNG", "SAHOL": "SABANCI HOLDİNG", "BIMAS": "BİM MAĞAZALAR",
    "FROTO": "FORD OTOSAN", "TOASO": "TOFAŞ OTO", "PGSUS": "PEGASUS",
    "TCELL": "TURKCELL", "TTKOM": "TÜRK TELEKOM", "PETKM": "PETKİM",
    "SASA": "SASA POLYESTER", "HEKTS": "HEKTAŞ", "ENKAI": "ENKA İNŞAAT",
    "VESTL": "VESTEL", "ARCLK": "ARÇELİK", "KONTR": "KONTROLMATİK",
    "ASTOR": "ASTOR ENERJİ", "KOZAL": "KOZA ALTIN", "ODAS": "ODAŞ ELEKTRİK",
    "EKGYO": "EMLAK KONUT", "MGROS": "MİGROS", "DOAS": "DOĞUŞ OTOMOTİV"
}

# --- 4. API ---
try:
    api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=api_key)
except: st.error("API Key Hatası"); st.stop()

# --- 5. VERİ VE HESAPLAMA ---
def rsi_hesapla(data, window=14):
    try:
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    except: return 50

def veri_getir(sembol):
    try:
        hisse = yf.Ticker(sembol)
        hist = hisse.history(period="1y")
        if hist.empty: return None

        guncel_fiyat = hist['Close'].iloc[-1]
        try: bilgi = hisse.info
        except: bilgi = {}

        def guvenli(keys, default=0):
            for k in keys:
                if bilgi.get(k) is not None: return bilgi.get(k)
            return default

        fk = guvenli(['trailingPE', 'forwardPE'])
        if fk == 0:
            eps = guvenli(['trailingEps'])
            if eps != 0: fk = guncel_fiyat / eps

        pd_dd = guvenli(['priceToBook'])
        roe = guvenli(['returnOnEquity']) * 100
        buyume = guvenli(['revenueGrowth']) * 100
        
        hist['RSI'] = rsi_hesapla(hist)
        son_rsi = hist['RSI'].iloc[-1]
        
        onceki_kapanis = hist['Close'].iloc[-2]
        degisim = ((guncel_fiyat - onceki_kapanis) / onceki_kapanis) * 100

        puan = 0
        if roe > 30: puan += 30
        elif roe > 10: puan += 15
        elif roe > 0: puan += 10
        
        if 0 < fk < 10: puan += 30
        elif 10 <= fk < 20: puan += 15
        
        if 30 <= son_rsi <= 70: puan += 20
        if buyume > 20: puan += 20
        elif buyume > 0: puan += 10
        
        return {
            'ad': bilgi.get('longName', sembol),
            'sektor': bilgi.get('sector', 'BIST'),
            'ozet': bilgi.get('longBusinessSummary', ''),
            'fiyat': guncel_fiyat, 'degisim': degisim,
            'fk': fk, 'pd_dd': pd_dd, 'roe': roe, 'buyume': buyume,
            'rsi': son_rsi, 'puan': min(puan, 100), 'hist': hist
        }
    except: return None

def metni_temizle(metin):
    metin = re.sub(r'[^\x00-\x7F\u00C0-\u00FF\u0100-\u017F\s.,;:!?()"\'-]', '', metin)
    yasakli = ["approximately", "slightly", "doing", "trading", "However", "overall"]
    for k in yasakli: metin = metin.replace(k, "").replace(k.lower(), "")
    return metin

@st.cache_data(ttl=3600, show_spinner=False)
def ai_analiz(veri):
    try:
        prompt = f"""
        Rol: Kıdemli Finansal Mentor. Dil: Türkçe.
        Hisse: {veri['ad']}. Fiyat: {veri['fiyat']:.2f}, F/K: {veri['fk']:.2f}, ROE: %{veri['roe']:.1f}, Puan: {veri['puan']}.
        Özet: {veri['ozet'][:150]}...
        Görev: Şirketi kısaca tanıt. Risk ve fırsatları anlat.
        """
        chat = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.1
        )
        return metni_temizle(chat.choices[0].message.content)
    except: return "Analiz oluşturulamadı."

# --- HTML KART OLUŞTURUCU (FLIP CARD) ---
def create_card(title, value, formula_title, formula_desc):
    return f"""
    <div class="flip-card" onclick="this.classList.toggle('flipped')">
      <div class="flip-card-inner">
        <div class="flip-card-front">
          <div class="card-title">{title}</div>
          <div class="card-value">{value}</div>
          <div style="font-size:10px; color:#999; margin-top:5px;">(Çevirmek için tıkla 👆)</div>
        </div>
        <div class="flip-card-back">
          <div class="card-formula">{formula_title}</div>
          <div class="card-desc">{formula_desc}</div>
        </div>
      </div>
    </div>
    """

# --- 6. ARAYÜZ ---
st.sidebar.markdown("### 🎯 ODAK")
secim1 = st.sidebar.selectbox("Hisse Seçiniz", [f"{k} - {v}" for k, v in BIST_SIRKETLERI.items()])
kod1 = secim1.split(" - ")[0] + ".IS"
analyze_btn = st.sidebar.button("ANALİZ ET")

st.sidebar.markdown("---")
with st.sidebar.expander("Nasıl Kullanılır?"):
    st.info("Kutuların üzerine tıklayarak formüllerini görebilirsiniz.")

if analyze_btn:
    with st.spinner('ODAK motoru çalışıyor...'):
        data = veri_getir(kod1)
        
        if data:
            # HERO
            st.markdown(f"""
            <div class='hero-box'>
                <div style='color:#888; font-size:12px; letter-spacing:2px;'>{data['sektor']}</div>
                <h1 class='company-name'>{data['ad']}</h1>
                <div style='font-size:32px; font-weight:700; margin-top:10px;'>
                    {data['fiyat']:.2f} ₺ 
                    <span style='font-size:18px; color:{'#27ae60' if data['degisim']>0 else '#c0392b'};'>
                        %{data['degisim']:.2f}
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # KARTLAR VE PUAN
            col_score, col_metrics = st.columns([1, 3])
            
            with col_score:
                renk = "#27ae60" if data['puan'] >= 80 else ("#f1c40f" if data['puan'] >= 50 else "#e74c3c")
                durum = "MÜKEMMEL" if data['puan'] >= 80 else ("İYİ / ORTA" if data['puan'] >= 50 else "RİSKLİ")
                st.markdown(f"""
                <div class='score-card'>
                    <div style='font-size:12px; opacity:0.7;'>SAĞLIK PUANI</div>
                    <div style='font-size:64px; font-weight:800; line-height:1;'>{data['puan']}</div>
                    <div style='color:{renk}; margin-top:10px; font-weight:bold;'>{durum}</div>
                </div>
                """, unsafe_allow_html=True)

            with col_metrics:
                # Verileri Hazırla
                fk_val = f"{data['fk']:.2f}" if data['fk'] > 0 else "-"
                roe_val = f"%{data['roe']:.1f}" if data['roe'] != 0 else "-"
                buyume_val = f"%{data['buyume']:.1f}" if data['buyume'] != 0 else "-"
                rsi_val = f"{data['rsi']:.1f}"

                # Kartları HTML Olarak Oluştur (Grid Yapısı)
                c1, c2 = st.columns(2)
                
                with c1:
                    # F/K KARTI
                    st.markdown(create_card(
                        "F/K ORANI", fk_val, 
                        "Fiyat / Hisse Başı Kar", 
                        "Şirkete yatırdığın parayı kaç yılda geri alacağını gösterir. Düşük olması (0-10) ucuzluk belirtisidir."
                    ), unsafe_allow_html=True)
                    
                    # BÜYÜME KARTI
                    st.markdown(create_card(
                        "BÜYÜME (Yıllık)", buyume_val,
                        "(Bu Yıl - Geçen Yıl) / Geçen Yıl",
                        "Şirketin cirosunun geçen seneye göre ne kadar arttığını gösterir."
                    ), unsafe_allow_html=True)

                with c2:
                    # ROE KARTI
                    st.markdown(create_card(
                        "ROE (Karlılık)", roe_val,
                        "Net Kar / Özkaynaklar",
                        "Şirketin ortakların parasını ne kadar verimli kullandığını gösterir. %30 üstü harikadır."
                    ), unsafe_allow_html=True)

                    # RSI KARTI
                    st.markdown(create_card(
                        "RSI (Teknik)", rsi_val,
                        "Güç Endeksi Formülü",
                        "Hisseye olan talebi ölçer. 30 altı 'Ucuz', 70 üstü 'Pahalı' sinyali verebilir."
                    ), unsafe_allow_html=True)

            # GRAFİK & AI
            st.markdown("---")
            g1, g2 = st.columns([2, 1])
            with g1:
                st.markdown("### 📉 Teknik Analiz")
                fig = go.Figure(data=[go.Candlestick(x=data['hist'].index, open=data['hist']['Open'], 
                                high=data['hist']['High'], low=data['hist']['Low'], close=data['hist']['Close'])])
                fig.update_layout(height=400, template="plotly_white", margin=dict(t=10,b=0,l=0,r=0))
                st.plotly_chart(fig, use_container_width=True)
            
            with g2:
                st.markdown("### 🧠 ODAK Görüşü")
                yorum = ai_analiz(data)
                st.markdown(f"<div class='ai-card'>{yorum}</div>", unsafe_allow_html=True)

        else:
            st.warning("Veri alınamadı.")
else:
    st.markdown("<br><br><h1 style='text-align:center;'>🎯 ODAK</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#666;'>Analiz için sol menüden hisse seçin.</p>", unsafe_allow_html=True)
