import streamlit as st
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(page_title="Symulator Ekstraklasy Pro", page_icon="⚽", layout="wide")

# 🌟 MAGIA CSS: Działa tylko na ekranach mobilnych (max-width: 768px)
st.markdown("""
<style>
/* Ściskamy kropki (1 X 2), aby nigdy nie łamały się do nowej linii (dla PC i mobile) */
div[data-testid="stVerticalBlockBorderWrapper"] div[role="radiogroup"] {
    flex-wrap: nowrap !important;
    gap: 8px !important;
}

/* Reguły TYLKO dla telefonów */
@media (max-width: 768px) {
    div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        align-items: center !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="column"] {
        min-width: 0 !important;
        width: auto !important;
        flex: 1 1 0% !important;
        padding: 0 2px !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] p {
        font-size: 13px !important;
    }
}
</style>
""", unsafe_allow_html=True)

st.title("⚽ Zaawansowany Symulator Ekstraklasy")

@st.cache_data(ttl=3600)
def pobierz_dane_z_api():
    url = "https://free-api-live-football-data.p.rapidapi.com/football-get-all-matches-by-league?leagueid=196"
    headers = {
        "x-rapidapi-host": "free-api-live-football-data.p.rapidapi.com",
        "x-rapidapi-key": st.secrets["RAPIDAPI_KEY"] # <-- ZMIEŃ NA SWÓJ KLUCZ
    }
    try:
        response = requests.get(url, headers=headers)
        return response.json()
    except: return {}

dane_json = pobierz_dane_z_api()
mecze_z_api = dane_json.get("response", {}).get("matches", [])

def skrot_nazwy(nazwa):
    slownik = {
        "Legia Warszawa": "LEG", "Lech Poznan": "LPO", "Lech Poznań": "LPO",
        "Jagiellonia Bialystok": "JAG", "Jagiellonia Białystok": "JAG",
        "Rakow Czestochowa": "RCZ", "Raków Częstochowa": "RCZ",
        "Pogon Szczecin": "POG", "Pogoń Szczecin": "POG",
        "Gornik Zabrze": "GÓR", "Górnik Zabrze": "GÓR",
        "Zaglebie Lubin": "ZAG", "Zagłębie Lubin": "ZAG",
        "Lechia Gdansk": "LGD", "Lechia Gdańsk": "LGD",
        "Wisla Plock": "WPŁ", "Wisła Płock": "WPŁ",
        "Termalica Nieciecza": "TER", "Piast Gliwice": "PIA",
        "Stal Mielec": "STA", "Cracovia": "CRA", "Korona Kielce": "KOR", 
        "Radomiak Radom": "RAD", "Puszcza Niepolomice": "PUS", 
        "Puszcza Niepołomice": "PUS", "Warta Poznan": "WAR", 
        "Warta Poznań": "WAR", "GKS Katowice": "GKS", "Motor Lublin": "MOT"
    }
    return slownik.get(nazwa, nazwa[:3].upper())

st.sidebar.header("Ustawienia Tabeli")
wybrana_data = st.sidebar.date_input("Pokaż bazową tabelę na dzień:", datetime.now().date())

st.sidebar.divider()
tryb_symulacji = st.sidebar.radio("🕹️ Tryb symulacji:", ["1X2 (Szybki)", "Dokładny wynik"])

typ_tabeli = st.sidebar.radio("🔍 Klasyfikacja:", ["Wszystkie mecze", "Tylko Domowe", "Tylko Wyjazdowe"])
limit_meczow = st.sidebar.number_input("Tabela Formy (ostatnie X):", min_value=0, max_value=34, value=0)
uwzglednij_kary = st.sidebar.checkbox("Kara -5 pkt (Lechia)", value=True)

if st.sidebar.button("🗑️ Zresetuj symulacje", use_container_width=True):
    for key in list(st.session_state.keys()):
        if key.startswith("h_") or key.startswith("a_") or key.startswith("1x2_"):
            del st.session_state[key]
    st.rerun()

aktywne_symulacje = {}
if tryb_symulacji == "Dokładny wynik":
    for key, val in st.session_state.items():
        if key.startswith('h_') and str(val).isdigit():
            m_id = key.split('_')[1]
            val_a = st.session_state.get(f'a_{m_id}', '')
            if str(val_a).isdigit():
                aktywne_symulacje[m_id] = {'h': int(val), 'a': int(val_a)}
else:
    for key, val in st.session_state.items():
        if key.startswith('1x2_') and val in ["1", "X", "2"]:
            m_id = key.split('_')[1]
            if val == "1": aktywne_symulacje[m_id] = {'h': 1, 'a': 0}
            elif val == "X": aktywne_symulacje[m_id] = {'h': 0, 'a': 0}
            elif val == "2": aktywne_symulacje[m_id] = {'h': 0, 'a': 1}

def generuj_tabele(lista, data_g, sym, typ, lim, kary):
    stat = {}
    licz = {}
    wm = []
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
        if t not in stat: stat[t] = {'M': 0, 'PKT': 0, 'BZ': 0, 'BS': 0}; licz[t] = 0
        if lim > 0 and licz[t] >= lim: return
        stat[t]['M']+=1; licz[t]+=1; stat[t]['BZ']+=gz; stat[t]['BS']+=gs
        if gz>gs: stat[t]['PKT']+=3
        elif gz==gs: stat[t]['PKT']+=1

    for m in wm:
        if typ in ["Wszystkie mecze", "Tylko Domowe"]: add(m['h'], m['gh'], m['ga'])
        if typ in ["Wszystkie mecze", "Tylko Wyjazdowe"]: add(m['a'], m['ga'], m['gh'])
    if kary:
        for n in ["Lechia Gdansk", "Lechia Gdańsk"]:
            if n in stat: stat[n]['PKT'] -= 5
    df = pd.DataFrame.from_dict(stat, orient='index').reset_index()
    if not df.empty:
        df.rename(columns={'index': 'Drużyna'}, inplace=True)
        df['+/-'] = df['BZ'] - df['BS']
        df = df.sort_values(by=['PKT', '+/-'], ascending=False).reset_index(drop=True)
        df.index += 1
    return df

if mecze_z_api:
    c1, c2 = st.columns([1.5, 1.2])
    with c1:
        st.subheader(f"📊 Tabela")
        res = generuj_tabele(mecze_z_api, wybrana_data, aktywne_symulacje, typ_tabeli, limit_meczow, uwzglednij_kary)
        # ZMIANA: Tabela znów ma pozycje (brak hide_index) i stałą, przewijaną wysokość dopasowaną do prawego panelu
        st.dataframe(res, use_container_width=True, height=710)
        
    with c2:
        st.subheader("🔮 Symulacja")
        # ZMIANA: Stała wysokość i border, by panel przewijał się ładnie obok tabeli na PC
        with st.container(height=710, border=True):
            for m in mecze_z_api:
                st_obj = m.get('status', {})
                if not st_obj.get('finished') and not st_obj.get('cancelled'):
                    dm = pd.to_datetime(st_obj.get('utcTime'), errors='coerce')
                    if pd.notnull(dm) and dm.date() >= wybrana_data:
                        h, a, mid = m['home']['name'], m['away']['name'], str(m['id'])
                        sh, sa = skrot_nazwy(h), skrot_nazwy(a)
                        
                        if tryb_symulacji == "1X2 (Szybki)":
                            # ZMIANA: Ciasny układ z buforami na krańcach specjalnie pod PC
                            col1, col2, col3, col4, col5 = st.columns([0.7, 1.8, 2.2, 1.8, 0.5])
                            with col1: st.markdown(f"<div style='font-size:0.85em; color:gray; padding-top:6px;'>{dm.strftime('%d.%m')}</div>", unsafe_allow_html=True)
                            with col2: st.markdown(f"<div style='text-align:right; padding-top:4px;'><b>{sh}</b></div>", unsafe_allow_html=True)
                            with col3: st.radio("1X2", ["1", "X", "2"], key=f"1x2_{mid}", label_visibility="collapsed", horizontal=True, index=None)
                            with col4: st.markdown(f"<div style='text-align:left; padding-top:4px;'><b>{sa}</b></div>", unsafe_allow_html=True)
                        else:
                            # ZMIANA: Podobny, ciasny układ dla pól tekstowych
                            col1, col2, col3, col4, col5, col6 = st.columns([0.7, 2.0, 1.2, 1.2, 2.0, 0.5])
                            with col1: st.markdown(f"<div style='font-size:0.85em; color:gray; padding-top:12px;'>{dm.strftime('%d.%m')}</div>", unsafe_allow_html=True)
                            with col2: st.markdown(f"<div style='text-align:right; padding-top:8px;'><b>{sh}</b></div>", unsafe_allow_html=True)
                            with col3: st.text_input("H", key=f"h_{mid}", label_visibility="collapsed")
                            with col4: st.text_input("A", key=f"a_{mid}", label_visibility="collapsed")
                            with col5: st.markdown(f"<div style='text-align:left; padding-top:8px;'><b>{sa}</b></div>", unsafe_allow_html=True)
else:
    st.warning("Brak danych z API.")