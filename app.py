import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from groq import Groq
import re
import numpy as np
import pandas as pd

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="ODAK | Freedom", page_icon="🎯", layout="wide")

# --- 2. CSS: PRESTİJLİ VE KARARLI GÖRÜNÜM ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    
    .stApp { background-color: #F8F9FA; color: #111; font-family: 'Inter', sans-serif; }

    /* SIDEBAR (BORDO & BEYAZ) */
    section[data-testid="stSidebar"] { background-color: #8B0000 !important; }
    section[data-testid="stSidebar"] * { color: #FFFFFF !important; }
    div[data-testid="stSidebar"] .stSelectbox > div > div { background-color: rgba(255, 255, 255, 0.15) !important; border: 1px solid rgba(255, 255, 255, 0.3) !important; color: white !important; }
    div[data-testid="stSidebar"] .stButton > button { background-color: white !important; color: #8B0000 !important; font-weight: 800 !important; border: none; padding: 12px; width: 100%; transition: transform 0.2s; }
    div[data-testid="stSidebar"] .stButton > button:hover { transform: scale(1.02); background-color: #f0f0f0 !important; }

    /* KART TASARIMLARI */
    .hero-box { text-align: center; padding: 30px; margin-bottom: 20px; background: white; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.03); }
    .company-name { font-size: 38px; font-weight: 800; color: #111; margin: 0; }
    
    /* Metrik Kutuları */
    div[data-testid="stMetric"] { background-color: #FFFFFF !important; border: 1px solid #E5E5E5 !important; border-radius: 12px !important; box-shadow: 0 2px 5px rgba(0,0,0,0.02) !important; padding: 15px !important; }
    div[data-testid="stMetric"] label { color: #777 !important; font-size: 13px !important; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #111 !important; font-size: 24px !important; }

    /* ÖZEL KUTULAR */
    .score-card { background: #1D1D1F; color: white; padding: 25px; border-radius: 16px; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.15); }
    .ai-card { background: #fff; border-left: 5px solid #111; padding: 25px; border-radius: 8px; box-shadow: 0 5px 20px rgba(0,0,0,0.05); color: #333; line-height: 1.6; }
    .dividend-box { background: linear-gradient(135deg, #004d00 0%, #000000 100%); color: white; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px; }
    
    /* PROGRESS BAR KAPSAYICI */
    .progress-container { background: #e0e0e0; border-radius: 20px; height: 25px; width: 100%; margin: 10px 0; overflow: hidden; }
    .progress-fill { height: 100%; border-radius: 20px; background: #27ae60; transition: width 1s ease-in-out; }
    </style>
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
    "EKGYO": "EMLAK KONUT", "MGROS": "MİGROS", "DOAS": "DOĞUŞ OTOMOTİV",
    "VESBE": "VESTEL BEYAZ EŞYA", "ENJSA": "ENERJİSA"
}

# --- 4. API ---
try:
    api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=api_key)
except: st.error("API Key Hatası"); st.stop()

# --- 5. VERİ VE HESAPLAMA MOTORU ---
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
        hist = hisse.history(period="1y") # 1 Yıllık veri
        hist_5y = hisse.history(period="5y") # Temettü geçmişi için 5 yıllık
        
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
        
        # Temettü Verisi
        temettu_verimi = guvenli(['dividendYield']) * 100 # % olarak
        # Eğer yfinance yield vermezse, son 1 yıldaki temettüleri toplayıp fiyata böl
        if temettu_verimi == 0:
            temettuler = hisse.dividends
            if not temettuler.empty:
                son_yil_temettu = temettuler.loc[str(pd.Timestamp.now().year - 1):].sum()
                if son_yil_temettu > 0:
                    temettu_verimi = (son_yil_temettu / guncel_fiyat) * 100

        hist['RSI'] = rsi_hesapla(hist)
        son_rsi = hist['RSI'].iloc[-1]
        onceki_kapanis = hist['Close'].iloc[-2]
        degisim = ((guncel_fiyat - onceki_kapanis) / onceki_kapanis) * 100

        # Yıllık Büyüme (CAGR) Tahmini
        # Son 1 yıldaki fiyat değişimi + Temettü verimi = Toplam Getiri Beklentisi
        fiyat_buyumesi = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
        # Tahmin için biraz konservatif olalım (Max %100 büyüme alalım ki uçuk rakamlar çıkmasın)
        toplam_yillik_getiri = min(fiyat_buyumesi + temettu_verimi, 120) 
        if toplam_yillik_getiri < 0: toplam_yillik_getiri = 0 # Negatifse 0 al

        puan = 0
        if roe > 30: puan += 30
        elif roe > 10: puan += 15
        if 0 < fk < 12: puan += 30
        elif 12 <= fk < 20: puan += 15
        if temettu_verimi > 5: puan += 20 # Temettüye ek puan
        elif temettu_verimi > 2: puan += 10
        if 30 <= son_rsi <= 70: puan += 20

        return {
            'ad': bilgi.get('longName', sembol), 'sektor': bilgi.get('sector', 'BIST'),
            'ozet': bilgi.get('longBusinessSummary', ''), 'fiyat': guncel_fiyat, 
            'degisim': degisim, 'fk': fk, 'pd_dd': pd_dd, 'roe': roe, 'buyume': buyume,
            'rsi': son_rsi, 'temettu_verimi': temettu_verimi, 'puan': min(puan, 100), 
            'hist': hist, 'toplam_yillik_getiri': toplam_yillik_getiri, 'dividends': hisse.dividends
        }
    except Exception as e: 
        print(e)
        return None

def metni_temizle(metin):
    metin = re.sub(r'[^\x00-\x7F\u00C0-\u00FF\u0100-\u017F\s.,;:!?()"\'-]', '', metin)
    yasakli = ["approximately", "slightly", "doing", "trading", "However"]
    for k in yasakli: metin = metin.replace(k, "").replace(k.lower(), "")
    return metin

@st.cache_data(ttl=3600, show_spinner=False)
def ai_analiz(mod, veri):
    try:
        if mod == "TEMETTU":
            prompt = f"""
            Rol: Temettü Yatırım Uzmanı. Dil: Türkçe. Hisse: {veri['ad']}.
            Veriler: Temettü Verimi %{veri['temettu_verimi']:.2f}, Fiyat {veri['fiyat']:.2f}, Puan {veri['puan']}.
            Görev: Bu şirket 'Temettü Emekliliği' için uygun mu? Temettü verimi enflasyona karşı korur mu?
            Yatırım tavsiyesi vermeden yorumla.
            """
        elif mod == "HEDEF":
             prompt = f"""
            Rol: Finansal Koç. Dil: Türkçe. Hisse: {veri['ad']}.
            Durum: Kullanıcı bu hisseyle birikim yapıyor. Yıllık büyüme potansiyeli %{veri['toplam_yillik_getiri']:.1f}.
            Görev: Kullanıcıya 'Bileşik Getiri'nin gücünü ve sabırlı olmanın önemini anlatan kısa, motive edici bir paragraf yaz.
            """
        else:
            prompt = f"""
            Rol: Finansal Analist. Dil: Türkçe. Hisse: {veri['ad']}. 
            Veriler: F/K {veri['fk']:.2f}, ROE %{veri['roe']:.1f}, Puan {veri['puan']}.
            Görev: Şirketi kısaca anlat. Risk ve fırsatları yorumla.
            """
        chat = client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model="llama-3.3-70b-versatile", temperature=0.1)
        return metni_temizle(chat.choices[0].message.content)
    except: return "Analiz yok."

# --- 6. ARAYÜZ ---
st.sidebar.markdown("### 🎯 ODAK")

if 'analiz_aktif' not in st.session_state: st.session_state.analiz_aktif = False

# MOD SEÇİCİ
mod = st.sidebar.radio("MOD SEÇİNİZ", ["📊 GENEL ANALİZ", "🎯 HEDEF SİMÜLASYONU", "💸 TEMETTÜ YATIRIMI"])
st.sidebar.markdown("---")

list_secenekler = [f"{k} - {v}" for k, v in BIST_SIRKETLERI.items()]
secim1 = st.sidebar.selectbox("Hisse Seçiniz", list_secenekler, index=0)
kod1 = secim1.split(" - ")[0] + ".IS"
analyze_btn = st.sidebar.button("ANALİZİ BAŞLAT")

if analyze_btn: st.session_state.analiz_aktif = True

if st.session_state.analiz_aktif:
    data = veri_getir(kod1)
    
    if data:
        # ORTAK BAŞLIK (HER MODDA GÖRÜNÜR)
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

        # --- MOD 1: GENEL ANALİZ ---
        if mod == "📊 GENEL ANALİZ":
            c1, c2 = st.columns([1, 3])
            with c1:
                renk = "#27ae60" if data['puan'] >= 80 else ("#f1c40f" if data['puan'] >= 50 else "#e74c3c")
                durum = "MÜKEMMEL" if data['puan'] >= 80 else ("İYİ" if data['puan'] >= 50 else "RİSKLİ")
                st.markdown(f"""<div class='score-card'><div style='font-size:12px; opacity:0.7;'>SAĞLIK PUANI</div><div style='font-size:64px; font-weight:800;'>{data['puan']}</div><div style='color:{renk}; font-weight:bold;'>{durum}</div></div>""", unsafe_allow_html=True)
            with c2:
                m1, m2 = st.columns(2)
                m1.metric("F/K Oranı", f"{data['fk']:.2f}" if data['fk']>0 else "-")
                m1.metric("ROE (Karlılık)", f"%{data['roe']:.1f}")
                m2.metric("Temettü Verimi", f"%{data['temettu_verimi']:.2f}")
                m2.metric("RSI", f"{data['rsi']:.1f}")
            
            st.markdown("---")
            g1, g2 = st.columns([2, 1])
            with g1:
                st.markdown("### 📉 Teknik Görünüm")
                fig = go.Figure(data=[go.Candlestick(x=data['hist'].index, open=data['hist']['Open'], high=data['hist']['High'], low=data['hist']['Low'], close=data['hist']['Close'])])
                fig.update_layout(height=400, template="plotly_white", margin=dict(t=10,b=0,l=0,r=0))
                st.plotly_chart(fig, use_container_width=True)
            with g2:
                st.markdown("### 🧠 ODAK Görüşü")
                yorum = ai_analiz("GENEL", data)
                st.markdown(f"<div class='ai-card'>{yorum}</div>", unsafe_allow_html=True)

        # --- MOD 2: HEDEF SİMÜLASYONU (Custom Goals) ---
        elif mod == "🎯 HEDEF SİMÜLASYONU":
            st.markdown("### 🔮 Gelecek Planlayıcı")
            st.info("Kendi hedefini belirle, bileşik getirinin gücüyle ne zaman ulaşacağını hesaplayalım.")

            c_inp1, c_inp2, c_inp3 = st.columns(3)
            hedef_isim = c_inp1.text_input("Hedefin Adı (Örn: Ev, Araba)", "Finansal Özgürlük")
            hedef_tutar = c_inp2.number_input("Hedef Tutar (TL)", min_value=1000, value=1000000, step=10000)
            mevcut_lot = c_inp3.number_input("Şu An Kaç Lotun Var?", min_value=0, value=500)
            
            # Hesaplama Motoru
            mevcut_tutar = mevcut_lot * data['fiyat']
            if mevcut_tutar == 0: mevcut_tutar = 1 # Bölme hatası olmasın
            
            eksik_tutar = max(0, hedef_tutar - mevcut_tutar)
            tamamlanma = min((mevcut_tutar / hedef_tutar) * 100, 100)
            
            # Bileşik Faiz ile Zaman Tahmini: FV = PV * (1+r)^t
            # t = ln(FV/PV) / ln(1+r)
            # r = Aylık Büyüme (Yıllık / 12)
            
            tahmini_yil = 99
            aylik_buyume = (data['toplam_yillik_getiri'] / 100) / 12 # Basit aylık
            
            if mevcut_tutar > 0 and aylik_buyume > 0 and eksik_tutar > 0:
                ay_sayisi = np.log(hedef_tutar / mevcut_tutar) / np.log(1 + aylik_buyume)
                tahmini_yil = ay_sayisi / 12
            
            # Görselleştirme
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                <div style='background:white; padding:20px; border-radius:12px; text-align:center; border:1px solid #ddd;'>
                    <div style='color:#666; font-size:14px;'>HEDEFİN</div>
                    <div style='font-size:28px; font-weight:bold;'>{hedef_isim}</div>
                    <div style='font-size:24px; color:#111; margin-top:5px;'>{hedef_tutar:,.0f} ₺</div>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                <div style='background:#1D1D1F; color:white; padding:20px; border-radius:12px; text-align:center;'>
                    <div style='color:#ccc; font-size:14px;'>MEVCUT BİRİKİM</div>
                    <div style='font-size:32px; font-weight:bold;'>{mevcut_tutar:,.0f} ₺</div>
                    <div style='font-size:14px; margin-top:5px; color:#f1c40f'>%{tamamlanma:.1f} Tamamlandı</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown(f"""
            <div style='margin-top:20px;'>
                <div class='progress-container'>
                    <div class='progress-fill' style='width: {tamamlanma}%;'></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Tahmin Sonucu
            if eksik_tutar > 0:
                if tahmini_yil < 50:
                    yil_str = int(tahmini_yil)
                    ay_str = int((tahmini_yil - yil_str) * 12)
                    mesaj = f"Bu hissenin geçmiş performansı (%{data['toplam_yillik_getiri']:.1f} Yıllık Getiri) devam ederse ve temettüleri tekrar yatırırsan; hedefine yaklaşık <b>{yil_str} Yıl {ay_str} Ay</b> sonra ulaşabilirsin."
                else:
                    mesaj = "Hedefe ulaşmak mevcut birikimle çok uzun sürebilir. Düzenli ekleme yapmalısın."
                
                st.markdown(f"""
                <div style='background:linear-gradient(135deg, #2c3e50 0%, #000000 100%); color:white; padding:20px; border-radius:12px; margin-top:20px; border-left:5px solid #f1c40f;'>
                    <div style='font-weight:bold; font-size:18px;'>🚀 Zaman Makinesi</div>
                    <div style='margin-top:5px; font-size:15px;'>{mesaj}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.balloons()
                st.success("Tebrikler! Hedef tutara ulaştınız.")

            st.markdown("---")
            st.markdown("### 🧠 Koç Görüşü")
            yorum = ai_analiz("HEDEF", data)
            st.markdown(f"<div class='ai-card'>{yorum}</div>", unsafe_allow_html=True)

        # --- MOD 3: TEMETTÜ YATIRIMI (YENİ!) ---
        elif mod == "💸 TEMETTÜ YATIRIMI":
            st.markdown("### 🏔️ Kar Topu Etkisi")
            
            col_div1, col_div2 = st.columns([1, 2])
            
            with col_div1:
                verim = data['temettu_verimi']
                renk_div = "#27ae60" if verim > 5 else ("#f1c40f" if verim > 2 else "#e74c3c")
                
                st.markdown(f"""
                <div class='dividend-box'>
                    <div style='font-size:14px; opacity:0.8;'>TEMETTÜ VERİMİ</div>
                    <div style='font-size:48px; font-weight:bold;'>%{verim:.2f}</div>
                    <div style='font-size:12px; margin-top:10px;'>Her 100 TL'lik yatırımın, yılda {verim:.2f} TL nakit doğuruyor.</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Temettü Hesaplayıcı
                st.markdown("#### 🧮 Gelir Hesapla")
                lot_temettu = st.number_input("Elindeki Lot", value=1000)
                tahmini_gelir = lot_temettu * data['fiyat'] * (verim / 100)
                st.info(f"Yıllık Tahmini Nakit: **{tahmini_gelir:,.2f} TL**")

            with col_div2:
                # Temettü Geçmişi Grafiği
                st.markdown("#### 📅 Temettü Geçmişi")
                div_hist = data['dividends']
                if not div_hist.empty:
                    # Yıllara göre grupla
                    div_yearly = div_hist.resample('Y').sum()
                    div_yearly.index = div_yearly.index.year
                    
                    fig = go.Figure(data=[go.Bar(
                        x=div_yearly.index, 
                        y=div_yearly.values,
                        marker_color='#27ae60'
                    )])
                    fig.update_layout(
                        title="Yıllara Göre Hisse Başına Ödenen Temettü (TL)",
                        template="plotly_white",
                        height=300,
                        margin=dict(t=30, b=0, l=0, r=0)
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Bu şirketin kayıtlı temettü geçmişi bulunamadı.")

            st.markdown("---")
            st.markdown("### 🧠 Temettü Analisti")
            yorum = ai_analiz("TEMETTU", data)
            st.markdown(f"<div class='ai-card'>{yorum}</div>", unsafe_allow_html=True)

    else: st.warning("Veri Alınamadı.")
else:
    st.markdown("<br><br><h1 style='text-align:center;'>🎯 ODAK</h1>", unsafe_allow_html=True)
