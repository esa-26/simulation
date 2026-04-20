import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# ----------------- KONFIGURACJA STRONY -----------------
st.set_page_config(page_title="Symulator Ekstraklasy Pro", page_icon="⚽", layout="wide")
st.title("⚽ Zaawansowany Symulator Ekstraklasy")

# ----------------- POBIERANIE DANYCH -----------------
@st.cache_data(ttl=3600)
def pobierz_dane_z_api():
    url = "https://free-api-live-football-data.p.rapidapi.com/football-get-all-matches-by-league?leagueid=196"
    headers = {
        "x-rapidapi-host": "free-api-live-football-data.p.rapidapi.com",
        "x-rapidapi-key": st.secrets["RAPIDAPI_KEY"]
    }
    try:
        response = requests.get(url, headers=headers)
        return response.json()
    except Exception as e:
        st.error(f"Błąd połączenia z API: {e}")
        return {}

dane_json = pobierz_dane_z_api()
mecze_z_api = dane_json.get("response", {}).get("matches", [])

# ----------------- INTERFEJS BOCZNY (FILTRY) -----------------
st.sidebar.header("Ustawienia Tabeli")
wybrana_data = st.sidebar.date_input("Pokaż bazową tabelę na dzień:", datetime.now().date())

st.sidebar.divider()
st.sidebar.subheader("🔍 Filtry Zaawansowane")
typ_tabeli = st.sidebar.radio(
    "Klasyfikacja:", 
    ["Wszystkie mecze", "Tylko Domowe", "Tylko Wyjazdowe"]
)

limit_meczow = st.sidebar.number_input(
    "Tabela Formy (ostatnie X meczów):", 
    min_value=0, max_value=34, value=0, step=1,
    help="Wpisz 0, aby policzyć wszystkie mecze w sezonie. Wpisz np. 5, aby zobaczyć formę z ostatnich 5 spotkań."
)

# 🌟 NOWA FUNKCJA: KARY REGULAMINOWE
st.sidebar.divider()
st.sidebar.subheader("⚖️ Decyzje PZPN")
uwzglednij_kary = st.sidebar.checkbox("Uwzględnij karę -5 pkt (Lechia Gdańsk)", value=True)

st.sidebar.divider()
if st.sidebar.button("🗑️ Zresetuj symulacje", use_container_width=True):
    for key in list(st.session_state.keys()):
        if key.startswith("h_") or key.startswith("a_"):
            st.session_state[key] = ""
    st.rerun()
st.sidebar.caption("Wpisz wyniki z klawiatury w panelu głównym, aby symulować przyszłość.")

# ----------------- ZBIERANIE SYMULACJI -----------------
aktywne_symulacje = {}
for key, val_h in st.session_state.items():
    if key.startswith('h_'):
        val_h_str = str(val_h).strip()
        if val_h_str.isdigit():
            mecz_id = key.split('_')[1]
            val_a_str = str(st.session_state.get(f'a_{mecz_id}', '')).strip()
            if val_a_str.isdigit():
                aktywne_symulacje[mecz_id] = {'h': int(val_h_str), 'a': int(val_a_str)}

# ----------------- SILNIK PRZELICZAJĄCY -----------------
def generuj_tabele(lista_meczow, data_graniczna, symulacje, typ, limit, kary_aktywne):
    statystyki = {}
    liczniki_meczow = {}
    wazne_mecze = []
    
    for mecz in lista_meczow:
        mecz_id = str(mecz.get('id', ''))
        status_obj = mecz.get('status', {})
        data_str = status_obj.get('utcTime')
        czy_zakonczony = status_obj.get('finished', False)
        
        if not data_str: continue
        data_meczu = pd.to_datetime(data_str, errors='coerce')
        if pd.isnull(data_meczu): continue
        
        gole_h, gole_a = None, None
        
        if mecz_id in symulacje:
            gole_h, gole_a = symulacje[mecz_id]['h'], symulacje[mecz_id]['a']
        elif data_meczu.date() <= data_graniczna and czy_zakonczony:
            gole_h, gole_a = mecz.get('home', {}).get('score'), mecz.get('away', {}).get('score')
            
        if gole_h is not None and gole_a is not None:
            wazne_mecze.append({
                'data': data_meczu,
                'gospodarz': mecz.get('home', {}).get('name', 'Nieznany'),
                'gosc': mecz.get('away', {}).get('name', 'Nieznany'),
                'gole_h': gole_h,
                'gole_a': gole_a
            })
            
    wazne_mecze.sort(key=lambda x: x['data'], reverse=True)
    
    def dodaj_statystyki(druzyna, gole_zdobyte, gole_stracone):
        if druzyna not in statystyki:
            statystyki[druzyna] = {'M': 0, 'PKT': 0, 'BZ': 0, 'BS': 0}
            liczniki_meczow[druzyna] = 0
            
        if limit > 0 and liczniki_meczow[druzyna] >= limit:
            return 
            
        statystyki[druzyna]['M'] += 1
        liczniki_meczow[druzyna] += 1
        statystyki[druzyna]['BZ'] += gole_zdobyte
        statystyki[druzyna]['BS'] += gole_stracone
        
        if gole_zdobyte > gole_stracone:
            statystyki[druzyna]['PKT'] += 3
        elif gole_zdobyte == gole_stracone:
            statystyki[druzyna]['PKT'] += 1

    for m in wazne_mecze:
        if typ in ["Wszystkie mecze", "Tylko Domowe"]:
            dodaj_statystyki(m['gospodarz'], m['gole_h'], m['gole_a'])
            
        if typ in ["Wszystkie mecze", "Tylko Wyjazdowe"]:
            dodaj_statystyki(m['gosc'], m['gole_a'], m['gole_h'])

    # 🌟 KROK DEDYKOWANY: Odbieranie punktów (jeśli checkbox jest zaznaczony)
    if kary_aktywne:
        # Sprawdzamy dwie formy zapisu, by uniknąć problemu z polskimi znakami w API
        for nazwa_lechii in ["Lechia Gdansk", "Lechia Gdańsk"]:
            if nazwa_lechii in statystyki:
                statystyki[nazwa_lechii]['PKT'] -= 5

    df = pd.DataFrame.from_dict(statystyki, orient='index').reset_index()
    if not df.empty:
        df.rename(columns={'index': 'Drużyna'}, inplace=True)
        df['+/-'] = df['BZ'] - df['BS']
        df = df.sort_values(by=['PKT', '+/-'], ascending=[False, False]).reset_index(drop=True)
        df.index += 1
        df = df[['Drużyna', 'M', 'PKT', 'BZ', 'BS', '+/-']]
    return df

# ----------------- WIDOK GŁÓWNY -----------------
if mecze_z_api:
    col1, col2 = st.columns([1.5, 1.2])

    with col1:
        tytul = f"📊 Tabela ({typ_tabeli})"
        if limit_meczow > 0:
            tytul += f" - Forma: ost. {limit_meczow} meczów"
        st.subheader(tytul)
        
        if len(aktywne_symulacje) > 0:
            st.success(f"Aktywne symulacje uwzględnione w tabeli: {len(aktywne_symulacje)}")
        
        # Przekazujemy stan naszego nowego checkboxa do funkcji ułożenia tabeli
        tabela = generuj_tabele(mecze_z_api, wybrana_data, aktywne_symulacje, typ_tabeli, limit_meczow, uwzglednij_kary)
        
        if not tabela.empty:
            st.dataframe(tabela, use_container_width=True, height=750)
        else:
            st.info("Brak meczów spełniających wybrane kryteria.")

    with col2:
        st.subheader("🔮 Panel Symulacji")
        st.caption("Wpisz z klawiatury wyniki nadchodzących spotkań:")
        
        licznik_przyszlych = 0
        with st.container(height=680, border=True):
            for m in mecze_z_api:
                status_obj = m.get('status', {})
                data_str = status_obj.get('utcTime')
                czy_zakonczony = status_obj.get('finished', False)
                czy_anulowany = status_obj.get('cancelled', False)
                mecz_id = str(m.get('id', ''))
                
                if data_str and not czy_zakonczony and not czy_anulowany: 
                    try:
                        data_meczu = pd.to_datetime(data_str, errors='coerce')
                        if pd.notnull(data_meczu) and data_meczu.date() >= wybrana_data:
                            licznik_przyszlych += 1
                            
                            gospodarz = m.get('home', {}).get('name', 'Nieznany')
                            gosc = m.get('away', {}).get('name', 'Nieznany')
                            data_format = data_meczu.strftime("%d.%m") 
                            
                            c1, c2, c3, c4, c5 = st.columns([1, 2.5, 1.2, 1.2, 2.5])
                            
                            with c1:
                                st.markdown(f"<div style='font-size: 0.85em; color: gray; margin-top: 10px;'>{data_format}</div>", unsafe_allow_html=True)
                            with c2:
                                st.markdown(f"<div style='text-align: right; font-weight: 500; margin-top: 5px;'>{gospodarz}</div>", unsafe_allow_html=True)
                            with c3:
                                st.text_input("H", key=f"h_{mecz_id}", label_visibility="collapsed", max_chars=2)
                            with c4:
                                st.text_input("A", key=f"a_{mecz_id}", label_visibility="collapsed", max_chars=2)
                            with c5:
                                st.markdown(f"<div style='text-align: left; font-weight: 500; margin-top: 5px;'>{gosc}</div>", unsafe_allow_html=True)
                            
                    except Exception:
                        continue

        if licznik_przyszlych == 0:
            st.success("Wszystkie zaplanowane mecze zostały rozegrane!")
else:
    st.warning("Brak danych z API.")