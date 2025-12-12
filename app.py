import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from groq import Groq
import re

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="ODAK | Life", page_icon="🎯", layout="wide")

# --- 2. CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    .stApp { background-color: #F8F9FA; color: #111; font-family: 'Inter', sans-serif; }
    
    /* SIDEBAR */
    section[data-testid="stSidebar"] { background-color: #8B0000 !important; }
    section[data-testid="stSidebar"] * { color: #FFFFFF !important; }
    div[data-testid="stSidebar"] .stButton > button { background: white !important; color: #8B0000 !important; font-weight:800; border:none; }

    /* FLIP CARD */
    .flip-card { background: transparent; width: 100%; height: 140px; perspective: 1000px; margin-bottom: 15px; cursor: pointer; }
    .flip-card-inner { position: relative; width: 100%; height: 100%; text-align: center; transition: transform 0.6s; transform-style: preserve-3d; box-shadow: 0 4px 8px rgba(0,0,0,0.1); border-radius: 16px; }
    .flip-card:active .flip-card-inner, .flip-card.flipped .flip-card-inner { transform: rotateY(180deg); }
    .flip-card-front, .flip-card-back { position: absolute; width: 100%; height: 100%; backface-visibility: hidden; border-radius: 16px; display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 10px; }
    .flip-card-front { background: #FFF; color: #111; border: 1px solid #E5E5E5; }
    .flip-card-back { background: #1D1D1F; color: #FFF; transform: rotateY(180deg); }
    
    /* HAYAT ENDEKSİ BARLARI */
    .life-bar-container { background: #e0e0e0; border-radius: 25px; margin: 20px 0; height: 30px; width: 100%; position: relative; overflow: hidden; }
    .life-bar-fill { height: 100%; border-radius: 25px; text-align: right; padding-right: 10px; color: white; font-weight: bold; line-height: 30px; transition: width 1s ease-in-out; }
    .loss-msg { color: #c0392b; font-weight: bold; padding: 15px; background: rgba(192, 57, 43, 0.1); border-radius: 12px; border-left: 5px solid #c0392b; margin-top: 15px; font-size: 15px; }
    .gain-msg { color: #27ae60; font-weight: bold; padding: 15px; background: rgba(39, 174, 96, 0.1); border-radius: 12px; border-left: 5px solid #27ae60; margin-top: 15px; font-size: 15px; }
    
    /* DİĞER */
    .hero-box { background: white; padding: 30px; border-radius: 16px; text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.03); margin-bottom: 20px; }
    .score-card { background: #1D1D1F; color: white; padding: 25px; border-radius: 16px; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.15); }
    .ai-card { background: #fff; border-left: 5px solid #111; padding: 25px; border-radius: 8px; box-shadow: 0 5px 20px rgba(0,0,0,0.05); line-height: 1.6; }
    </style>
    <script>function flipCard(e){e.classList.toggle("flipped")}</script>
    """, unsafe_allow_html=True)

# --- 3. LİSTE & KATALOG ---
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

HEDEFLER = {
    "☕ Starbucks Kahve": {"fiyat": 120, "ikon": "☕"},
    "🍔 Big Mac Menü": {"fiyat": 250, "ikon": "🍔"},
    "🎧 AirPods Pro 2": {"fiyat": 9000, "ikon": "🎧"},
    "✈️ Yurt Dışı Uçak Bileti": {"fiyat": 15000, "ikon": "✈️"},
    "📱 iPhone 16 Pro": {"fiyat": 85000, "ikon": "📱"},
    "💻 MacBook Air": {"fiyat": 45000, "ikon": "💻"},
    "🏍️ Vespa Motosiklet": {"fiyat": 250000, "ikon": "🏍️"},
    "🚗 Togg T10X": {"fiyat": 1400000, "ikon": "🚗"},
    "🏠 1+1 Ev Peşinatı": {"fiyat": 2000000, "ikon": "🏠"}
}

# --- 4. API ---
try:
    api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=api_key)
except: st.error("API Key Hatası"); st.stop()

# --- 5. VERİ MOTORU ---
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
        if fk == 0 and guvenli(['trailingEps']) != 0: fk = guncel_fiyat / guvenli(['trailingEps'])
        
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
        if 0 < fk < 12: puan += 30
        elif 12 <= fk < 20: puan += 15
        if 30 <= son_rsi <= 70: puan += 20
        if buyume > 20: puan += 20

        return {
            'ad': bilgi.get('longName', sembol), 'sektor': bilgi.get('sector', 'BIST'),
            'ozet': bilgi.get('longBusinessSummary', ''), 'fiyat': guncel_fiyat, 
            'degisim': degisim, 'fk': fk, 'pd_dd': pd_dd, 'roe': roe, 'buyume': buyume,
            'rsi': son_rsi, 'puan': min(puan, 100), 'hist': hist
        }
    except: return None

def metni_temizle(metin):
    metin = re.sub(r'[^\x00-\x7F\u00C0-\u00FF\u0100-\u017F\s.,;:!?()"\'-]', '', metin)
    yasakli = ["approximately", "slightly", "doing", "trading", "However"]
    for k in yasakli: metin = metin.replace(k, "").replace(k.lower(), "")
    return metin

@st.cache_data(ttl=3600, show_spinner=False)
def ai_analiz(veri):
    try:
        prompt = f"""
        Rol: Mentor. Dil: Türkçe. Hisse: {veri['ad']}. 
        Veriler: F/K {veri['fk']:.2f}, ROE %{veri['roe']:.1f}, Puan {veri['puan']}.
        Görev: Şirketi kısaca anlat. Risk ve fırsatları yorumla.
        """
        chat = client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model="llama-3.3-70b-versatile", temperature=0.1)
        return metni_temizle(chat.choices[0].message.content)
    except: return "Analiz yok."

def create_card(t, v, ft, fd):
    return f"""<div class="flip-card" onclick="this.classList.toggle('flipped')"><div class="flip-card-inner"><div class="flip-card-front"><div class="card-title">{t}</div><div class="card-value">{v}</div><div style="font-size:10px; color:#999;">(Çevir 👆)</div></div><div class="flip-card-back"><div class="card-formula">{ft}</div><div class="card-desc">{fd}</div></div></div></div>"""

# --- 6. ARAYÜZ ---
st.sidebar.markdown("### 🎯 ODAK")

# --- HAFIZA MEKANİZMASI (SESSION STATE) ---
if 'analiz_aktif' not in st.session_state:
    st.session_state.analiz_aktif = False

# MOD SEÇİMİ
mod = st.sidebar.radio("MOD SEÇİNİZ", ["📊 ANALİZ MODU", "🧬 HAYAT ENDEKSİ"])
st.sidebar.markdown("---")

list_secenekler = [f"{k} - {v}" for k, v in BIST_SIRKETLERI.items()]
secim1 = st.sidebar.selectbox("Hisse Seçiniz", list_secenekler, index=0)
kod1 = secim1.split(" - ")[0] + ".IS"
analyze_btn = st.sidebar.button("BAŞLAT")

# Butona basılınca hafızayı aktif et
if analyze_btn:
    st.session_state.analiz_aktif = True

# --- EĞER HAFIZA AKTİFSE SAYFAYI GÖSTER ---
if st.session_state.analiz_aktif:
    # Veriyi çek (Cache kullandığı için hızlıdır)
    data = veri_getir(kod1)
    
    if data:
        # HERO (Her iki modda da görünür)
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

        # --- MOD 1: KLASİK ANALİZ ---
        if mod == "📊 ANALİZ MODU":
            c1, c2 = st.columns([1, 3])
            with c1:
                renk = "#27ae60" if data['puan'] >= 80 else ("#f1c40f" if data['puan'] >= 50 else "#e74c3c")
                durum = "MÜKEMMEL" if data['puan'] >= 80 else ("İYİ" if data['puan'] >= 50 else "RİSKLİ")
                st.markdown(f"""<div class='score-card'><div style='font-size:12px; opacity:0.7;'>SAĞLIK PUANI</div><div style='font-size:64px; font-weight:800;'>{data['puan']}</div><div style='color:{renk}; font-weight:bold;'>{durum}</div></div>""", unsafe_allow_html=True)

            with c2:
                k1, k2 = st.columns(2)
                with k1:
                    st.markdown(create_card("F/K ORANI", f"{data['fk']:.2f}" if data['fk']>0 else "-", "Fiyat / Hisse Başı Kar", "Paranızı kaç yılda amorti edersiniz?"), unsafe_allow_html=True)
                    st.markdown(create_card("BÜYÜME", f"%{data['buyume']:.1f}", "Ciro Artışı", "Geçen yıla göre ne kadar büyüdü?"), unsafe_allow_html=True)
                with k2:
                    st.markdown(create_card("ROE (Karlılık)", f"%{data['roe']:.1f}", "Net Kar / Özkaynak", "Sermaye verimliliği. %30 üstü harikadır."), unsafe_allow_html=True)
                    st.markdown(create_card("RSI", f"{data['rsi']:.1f}", "Güç Endeksi", "30 altı ucuz, 70 üstü pahalı."), unsafe_allow_html=True)

            st.markdown("---")
            g1, g2 = st.columns([2, 1])
            with g1:
                st.markdown("### 📉 Teknik Analiz")
                fig = go.Figure(data=[go.Candlestick(x=data['hist'].index, open=data['hist']['Open'], high=data['hist']['High'], low=data['hist']['Low'], close=data['hist']['Close'])])
                fig.update_layout(height=400, template="plotly_white", margin=dict(t=10,b=0,l=0,r=0))
                st.plotly_chart(fig, use_container_width=True)
            with g2:
                st.markdown("### 🧠 ODAK Görüşü")
                yorum = ai_analiz(data)
                st.markdown(f"<div class='ai-card'>{yorum}</div>", unsafe_allow_html=True)

        # --- MOD 2: HAYAT ENDEKSİ ---
        else:
            st.markdown("### 🧬 Hayat Endeksi Simülasyonu")
            
            # Hedef Seçimi (Sayfa yenilense bile hafıza sayesinde burası çalışacak)
            col_in1, col_in2 = st.columns(2)
            with col_in1:
                secilen_hedef = st.selectbox("🎯 HEDEFİNİZ NEDİR?", list(HEDEFLER.keys()))
            with col_in2:
                lot_sayisi = st.number_input("Kaç Adet Hisseniz Var?", min_value=1, value=100, step=10)
            
            hedef_detay = HEDEFLER[secilen_hedef]
            hedef_fiyat = hedef_detay["fiyat"]
            portfoy_degeri = lot_sayisi * data['fiyat']
            
            # Hesaplamalar
            tamamlanma_orani = min((portfoy_degeri / hedef_fiyat) * 100, 100)
            gereken_lot = max(0, (hedef_fiyat - portfoy_degeri) / data['fiyat'])
            
            # GÖRSELLEŞTİRME
            c1, c2 = st.columns([1, 1])
            
            with c1:
                st.markdown(f"""
                <div style='background:white; padding:30px; border-radius:16px; border:1px solid #eee; text-align:center; box-shadow: 0 4px 20px rgba(0,0,0,0.05);'>
                    <div style='font-size:80px;'>{hedef_detay['ikon']}</div>
                    <div style='font-size:24px; font-weight:800; margin-top:10px;'>{secilen_hedef}</div>
                    <div style='font-size:18px; color:#666; margin-top:5px;'>Hedef Fiyat: <b>{hedef_fiyat:,.0f} ₺</b></div>
                </div>
                """, unsafe_allow_html=True)
            
            with c2:
                st.markdown(f"""
                <div style='background:#1D1D1F; color:white; padding:30px; border-radius:16px; text-align:center; height:100%; display:flex; flex-direction:column; justify-content:center; box-shadow: 0 10px 30px rgba(0,0,0,0.15);'>
                    <div style='font-size:14px; opacity:0.7; letter-spacing:1px;'>MEVCUT ALIM GÜCÜNÜZ</div>
                    <div style='font-size:48px; font-weight:800; margin:10px 0;'>{portfoy_degeri:,.0f} ₺</div>
                    <div style='font-size:18px;'>Hedefe <b style='color:#f1c40f'>{gereken_lot:,.0f}</b> Lot Kaldı</div>
                </div>
                """, unsafe_allow_html=True)

            # PROGRESS BAR
            renk_bar = "#27ae60" if tamamlanma_orani == 100 else "#3498db"
            st.markdown(f"""
            <div style='margin-top:30px; background:white; padding:20px; border-radius:16px; border:1px solid #eee;'>
                <div style='display:flex; justify-content:space-between; font-weight:bold; margin-bottom:10px; color:#333;'>
                    <span>Hedefe Uzaklık</span>
                    <span>%{tamamlanma_orani:.1f}</span>
                </div>
                <div class='life-bar-container'>
                    <div class='life-bar-fill' style='width: {tamamlanma_orani}%; background-color: {renk_bar};'>
                        {hedef_detay['ikon']}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # TERSİNE ÇEVİRME MODU
            gunluk_kazanc_tl = (portfoy_degeri * data['degisim']) / 100
            
            if gunluk_kazanc_tl < 0:
                st.markdown(f"""
                <div class='loss-msg'>
                    ⚠️ <b>DİKKAT:</b> Bugün hissendeki düşüş (%{data['degisim']:.2f}) yüzünden, hedefine giden yolda 
                    <b>{abs(gunluk_kazanc_tl):.0f} TL</b> eridi. 
                    Bu, hedeften yaklaşık <b>{(abs(gunluk_kazanc_tl)/hedef_fiyat)*100:.2f}%</b> uzaklaştığın anlamına geliyor.
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class='gain-msg'>
                    🚀 <b>HARİKA:</b> Bugün hissendeki yükseliş (%{data['degisim']:.2f}) sayesinde, hedefine 
                    <b>{gunluk_kazanc_tl:.0f} TL</b> daha yaklaştın! 
                    Böyle giderse hedefe beklenenden erken ulaşabilirsin.
                </div>
                """, unsafe_allow_html=True)

    else: st.warning("Veri Yok.")
else:
    st.markdown("<br><br><h1 style='text-align:center;'>🎯 ODAK</h1><p style='text-align:center;'>Mod seçin ve analize başlayın.</p>", unsafe_allow_html=True)
