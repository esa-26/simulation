import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# ----------------- KONFIGURACJA -----------------
st.set_page_config(page_title="Symulator Ligowy Pro", page_icon="⚽", layout="wide")

# CSS: Okrągłe kafelki i dociągnięcie gości
st.markdown("""
<style>
    [data-testid="stHorizontalBlock"] { align-items: center !important; gap: 0px !important; }
    [data-testid="stBaseButton-pills"] { border-radius: 20px !important; padding: 4px 12px !important; }
    div[data-testid="stPills"] > div { flex-wrap: nowrap !important; gap: 8px !important; }
    @media (max-width: 768px) {
        div[data-testid="column"] { min-width: 0 !important; flex: 1 1 auto !important; }
        .stMarkdown p { font-size: 11px !important; line-height: 1.1 !important; }
    }
</style>
""", unsafe_allow_html=True)

st.title("⚽ Zaawansowany Symulator Piłkarski")

# 🌟 INICJALIZACJA LICZNIKA RESETU (To nasza "Sól")
if 'reset_counter' not in st.session_state:
    st.session_state.reset_counter = 0

# ----------------- DANE -----------------
@st.cache_data(ttl=3600)
def pobierz_dane_z_api():
    url = "https://free-api-live-football-data.p.rapidapi.com/football-get-all-matches-by-league?leagueid=196"
    headers = {
        "x-rapidapi-host": "free-api-live-football-data.p.rapidapi.com",
        "x-rapidapi-key": st.secrets["RAPIDAPI_KEY"] # <-- TWÓJ KLUCZ
    }
    try:
        response = requests.get(url, headers=headers)
        return response.json()
    except: return {}

dane_json = pobierz_dane_z_api()
mecze_z_api = dane_json.get("response", {}).get("matches", [])

# ----------------- SIDEBAR (USTAWIENIA) -----------------
st.sidebar.header("Ustawienia")
wybrana_data = st.sidebar.date_input("Tabela na dzień:", datetime.now().date())
st.sidebar.divider()
tryb_symulacji = st.sidebar.radio("🕹️ Tryb typowania:", ["1X2 (Szybki)", "Dokładny wynik"])
typ_tabeli = st.sidebar.radio("🔍 Klasyfikacja:", ["Wszystkie mecze", "Tylko Domowe", "Tylko Wyjazdowe"])
limit_meczow = st.sidebar.number_input("Tabela Formy (ost. X):", min_value=0, max_value=34, value=0)
uwzglednij_kary = st.sidebar.checkbox("Kara -5 pkt (Lechia)", value=True)

# 🌟 SUPER RESET: Zmienia licznik wersji, co wymusza przerysowanie widgetów od zera
if st.sidebar.button("🗑️ Zresetuj symulacje (HOME)", use_container_width=True):
    st.session_state.reset_counter += 1
    st.cache_data.clear()
    st.rerun()

# ----------------- LOGIKA SYMULACJI -----------------
aktywne_symulacje = {}
rc = st.session_state.reset_counter

if tryb_symulacji == "Dokładny wynik":
    for key, val in st.session_state.items():
        if key.startswith(f'h_') and key.endswith(f'_{rc}') and str(val).isdigit():
            m_id = key.split('_')[1]
            val_a = st.session_state.get(f'a_{m_id}_{rc}', '')
            if str(val_a).isdigit():
                aktywne_symulacje[m_id] = {'h': int(val), 'a': int(val_a)}
else:
    for key, val in st.session_state.items():
        # Szukamy kluczy pasujących do obecnej wersji resetu
        if key.startswith(f'1x2_') and key.endswith(f'_{rc}') and val in ["1", "X", "2"]:
            m_id = key.split('_')[1]
            if val == "1": aktywne_symulacje[m_id] = {'h': 1, 'a': 0}
            elif val == "X": aktywne_symulacje[m_id] = {'h': 0, 'a': 0}
            elif val == "2": aktywne_symulacje[m_id] = {'h': 0, 'a': 1}

# ----------------- SILNIK TABELI (BZ-BS, Z-R-P, Forma) -----------------
def generuj_tabele(lista, data_g, sym, typ, lim, kary):
    stat = {}; licz = {}; wm = []
    for m in lista:
        m_id = str(m.get('id', ''))
        st_obj = m.get('status', {})
        ds = st_obj.get('utcTime')
        if not ds: continue
        dm = pd.to_datetime(ds, errors='coerce')
        gh, ga = None, None
        if m_id in sym:
            gh, ga = sym[m_id]['h'], sym[m_id]['a']
        elif dm.date() <= data_g and st_obj.get('finished'):
            gh, ga = m.get('home', {}).get('score'), m.get('away', {}).get('score')
        if gh is not None and ga is not None:
            wm.append({'d': dm, 'h': m['home']['name'], 'a': m['away']['name'], 'gh': gh, 'ga': ga})
    
    wm.sort(key=lambda x: x['d'], reverse=True)
    def add(t, gz, gs):
        if t not in stat: 
            stat[t] = {'M': 0, 'PKT': 0, 'Z': 0, 'R': 0, 'P': 0, 'BZ': 0, 'BS': 0, 'Historia': []}; licz[t] = 0
        if lim > 0 and licz[t] >= lim: return
        stat[t]['M']+=1; licz[t]+=1; stat[t]['BZ']+=gz; stat[t]['BS']+=gs
        if gz > gs: stat[t]['PKT'] += 3; stat[t]['Z'] += 1; stat[t]['Historia'].append('Z')
        elif gz == gs: stat[t]['PKT'] += 1; stat[t]['R'] += 1; stat[t]['Historia'].append('R')
        else: stat[t]['P'] += 1; stat[t]['Historia'].append('P')

    for m in wm:
        if typ in ["Wszystkie mecze", "Tylko Domowe"]: add(m['h'], m['gh'], m['ga'])
        if typ in ["Wszystkie mecze", "Tylko Wyjazdowe"]: add(m['a'], m['ga'], m['gh'])
    if kary:
        for n in ["Lechia Gdansk", "Lechia Gdańsk"]:
            if n in stat: stat[n]['PKT'] -= 5
            
    df = pd.DataFrame.from_dict(stat, orient='index').reset_index()
    if not df.empty:
        df.rename(columns={'index': 'Drużyna'}, inplace=True)
        df['Bramki'] = df['BZ'].astype(str) + '-' + df['BS'].astype(str)
        df['Z-R-P'] = df['Z'].astype(str) + '-' + df['R'].astype(str) + '-' + df['P'].astype(str)
        df['Forma'] = df['Historia'].apply(lambda x: "".join(x[:5]))
        df['diff'] = df['BZ'] - df['BS']
        df = df.sort_values(by=['PKT', 'diff'], ascending=[False, False]).reset_index(drop=True)
        df.index = range(1, len(df) + 1)
        df.index.name = 'Poz'; df = df.reset_index()
        df = df[['Poz', 'Drużyna', 'M', 'PKT', 'Bramki', 'Z-R-P', 'Forma']]
    return df

# ----------------- WIDOK GŁÓWNY -----------------
if mecze_z_api:
    c1, c2 = st.columns([1.5, 1.2])
    with c1:
        st.subheader("📊 Tabela")
        res = generuj_tabele(mecze_z_api, wybrana_data, aktywne_symulacje, typ_tabeli, limit_meczow, uwzglednij_kary)
        st.dataframe(res, use_container_width=True, height=750, hide_index=True)
        
    with c2:
        st.subheader("🔮 Symulacja")
        with st.container(height=750, border=True):
            for m in mecze_z_api:
                st_obj = m.get('status', {})
                if not st_obj.get('finished') and not st_obj.get('cancelled'):
                    dm = pd.to_datetime(st_obj.get('utcTime'), errors='coerce')
                    if pd.notnull(dm) and dm.date() >= wybrana_data:
                        h, a, mid = m['home']['name'], m['away']['name'], str(m['id'])
                        
                        if tryb_symulacji == "1X2 (Szybki)":
                            # 🌟 Klucz z wersją resetu wymusza "odznaczenie" przycisków
                            col1, col2, col3, col4, col5 = st.columns([0.6, 2.0, 1.4, 2.0, 0.1])
                            with col1: st.caption(dm.strftime('%d.%m'))
                            with col2: st.markdown(f"<div style='text-align:right; padding-top:8px;'><b>{h}</b></div>", unsafe_allow_html=True)
                            with col3:
                                st.pills("1X2", ["1", "X", "2"], key=f"1x2_{mid}_{rc}", label_visibility="collapsed", selection_mode="single")
                            with col4: st.markdown(f"<div style='text-align:left; padding-top:8px;'><b>{a}</b></div>", unsafe_allow_html=True)
                        else:
                            col1, col2, col3, col4, col5, col6 = st.columns([0.6, 2.0, 0.8, 0.8, 2.0, 0.1])
                            with col1: st.caption(dm.strftime('%d.%m'))
                            with col2: st.markdown(f"<div style='text-align:right; padding-top:8px;'><b>{h}</b></div>", unsafe_allow_html=True)
                            with col3: st.text_input("H", key=f"h_{mid}_{rc}", label_visibility="collapsed")
                            with col4: st.text_input("A", key=f"a_{mid}_{rc}", label_visibility="collapsed")
                            with col5: st.markdown(f"<div style='text-align:left; padding-top:8px;'><b>{a}</b></div>", unsafe_allow_html=True)
else:
    st.warning("Brak danych z API.")