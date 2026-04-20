import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# ----------------- CONFIGURATION -----------------
st.set_page_config(page_title="Pro Football Simulator", page_icon="⚽", layout="wide")

# CSS: Advanced alignment and WRAP BLOCKING
st.markdown("""
<style>
    /* Blokada zawijania rzędów i centrowanie */
    [data-testid="stHorizontalBlock"] { 
        align-items: center !important; 
        gap: 0px !important;
        flex-wrap: nowrap !important; /* Zakaz łamania kolumn do nowych linii */
    }
    
    /* STYLIZACJA KAFELKÓW (PILLS) - BLOKADA ZAWIJANIA */
    div[data-testid="stPills"] > div {
        flex-wrap: nowrap !important; /* Kluczowe: kafelki nigdy nie przejdą do nowej linii */
        justify-content: center !important;
        gap: 4px !important;
        min-width: 140px !important; /* Rezerwacja miejsca, żeby nie "pękły" */
    }

    /* Dopasowanie samych przycisków */
    [data-testid="stBaseButton-pills"] { 
        border-radius: 6px !important; 
        padding: 2px 10px !important;
        font-weight: bold !important;
        font-size: 14px !important;
    }

    /* Wyrównanie pól tekstowych */
    div[data-testid="stTextInput"] input {
        text-align: center !important;
    }

    /* Responsywność nazw - zapobieganie uciekaniu tekstu */
    .team-label {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
</style>
""", unsafe_allow_html=True)

st.title("⚽ Advanced League Simulator")

if 'reset_counter' not in st.session_state:
    st.session_state.reset_counter = 0

# ----------------- LEAGUE MAPPING -----------------
LEAGUES = {
    "Poland: Ekstraklasa": 196,
    "England: Premier League": 47,
    "Spain: La Liga": 87,
    "Germany: Bundesliga": 54,
    "Italy: Serie A": 55,
    "France: Ligue 1": 53,
    "Netherlands: Eredivisie": 57,
    "Portugal: Primeira Liga": 61,
    "England: Championship": 48,
    "Turkey: Süper Lig": 71,
    "Belgium: Pro League": 51,
    "Scotland: Premiership": 64
}

# ----------------- SIDEBAR -----------------
st.sidebar.header("🌍 League Selection")
selected_league_name = st.sidebar.selectbox("Select League:", list(LEAGUES.keys()))
league_id = LEAGUES[selected_league_name]

st.sidebar.divider()
st.sidebar.header("⚙️ Settings")
selected_date = st.sidebar.date_input("Table Date:", datetime.now().date())
sim_mode = st.sidebar.radio("🕹️ Prediction Mode:", ["1X2 (Quick)", "Correct Score"])
table_type = st.sidebar.radio("🔍 Standings Type:", ["All matches", "Home only", "Away only"])
form_limit = st.sidebar.number_input("Form Table (last X):", min_value=0, max_value=38, value=0)

if st.sidebar.button("🗑️ Reset All Simulation", use_container_width=True):
    st.session_state.reset_counter += 1
    st.cache_data.clear()
    st.rerun()

# ----------------- DATA FETCHING -----------------
@st.cache_data(ttl=3600)
def fetch_api_data(lid):
    url = f"https://free-api-live-football-data.p.rapidapi.com/football-get-all-matches-by-league?leagueid={lid}"
    headers = {
        "x-rapidapi-host": "free-api-live-football-data.p.rapidapi.com",
        "x-rapidapi-key": st.secrets["RAPIDAPI_KEY"]
    }
    try:
        response = requests.get(url, headers=headers)
        return response.json()
    except: return {}

data_json = fetch_api_data(league_id)
api_matches = data_json.get("response", {}).get("matches", [])

# ----------------- LOGIKA SYMULACJI -----------------
active_simulations = {}
rc = st.session_state.reset_counter

for key, val in st.session_state.items():
    if key.endswith(f'_{rc}'):
        m_id = key.split('_')[1]
        if key.startswith('1x2_') and val in ["1", "X", "2"]:
            if val == "1": active_simulations[m_id] = {'h': 1, 'a': 0}
            elif val == "X": active_simulations[m_id] = {'h': 0, 'a': 0}
            elif val == "2": active_simulations[m_id] = {'h': 0, 'a': 1}
        elif key.startswith('h_') and str(val).isdigit():
            val_a = st.session_state.get(f'a_{m_id}_{rc}', '')
            if str(val_a).isdigit():
                active_simulations[m_id] = {'h': int(val), 'a': int(val_a)}

# ----------------- STANDINGS ENGINE -----------------
def generate_table(matches_list, date_limit, sym, t_type, f_limit):
    stats = {}; counter = {}; processed = []
    for m in matches_list:
        m_id = str(m.get('id', ''))
        st_obj = m.get('status', {})
        match_utc = st_obj.get('utcTime')
        if not match_utc: continue
        m_date = pd.to_datetime(match_utc, errors='coerce')
        gh, ga = None, None
        if m_id in sym:
            gh, ga = sym[m_id]['h'], sym[m_id]['a']
        elif m_date.date() <= date_limit and st_obj.get('finished'):
            gh, ga = m.get('home', {}).get('score'), m.get('away', {}).get('score')
        if gh is not None and ga is not None:
            processed.append({'d': m_date, 'h': m['home']['name'], 'a': m['away']['name'], 'gh': gh, 'ga': ga})
    
    processed.sort(key=lambda x: x['d'], reverse=True)
    def add_stats(team, g_s, g_c):
        if team not in stats: 
            stats[team] = {'P': 0, 'Pts': 0, 'W': 0, 'D': 0, 'L': 0, 'GS': 0, 'GC': 0, 'History': []}
            counter[team] = 0
        if f_limit > 0 and counter[team] >= f_limit: return
        stats[team]['P']+=1; counter[team]+=1; stats[team]['GS']+=g_s; stats[team]['GC']+=g_c
        if g_s > g_c: stats[team]['Pts'] += 3; stats[team]['W'] += 1; stats[team]['History'].append('W')
        elif g_s == g_c: stats[team]['Pts'] += 1; stats[team]['D'] += 1; stats[team]['History'].append('D')
        else: stats[team]['L'] += 1; stats[team]['History'].append('L')

    for m in processed:
        if t_type in ["All matches", "Home only"]: add_stats(m['h'], m['gh'], m['ga'])
        if t_type in ["All matches", "Away only"]: add_stats(m['a'], m['ga'], m['gh'])
            
    df = pd.DataFrame.from_dict(stats, orient='index').reset_index()
    if not df.empty:
        df.rename(columns={'index': 'Team'}, inplace=True)
        df['Goals'] = df['GS'].astype(str) + '-' + df['GC'].astype(str)
        df['W-D-L'] = df['W'].astype(str) + '-' + df['D'].astype(str) + '-' + df['L'].astype(str)
        df['Form'] = df['History'].apply(lambda x: "".join(x[:5]))
        df['diff'] = df['GS'] - df['GC']
        df = df.sort_values(by=['Pts', 'diff', 'GS'], ascending=[False, False, False]).reset_index(drop=True)
        df.index = range(1, len(df) + 1)
        df.index.name = 'Pos'; df = df.reset_index()
        df = df[['Pos', 'Team', 'P', 'Pts', 'Goals', 'W-D-L', 'Form']]
    return df

# ----------------- MAIN VIEW -----------------
if api_matches:
    c1, c2 = st.columns([1.4, 1.3])
    with c1:
        st.subheader(f"📊 Standings: {selected_league_name}")
        table_res = generate_table(api_matches, selected_date, active_simulations, table_type, form_limit)
        st.dataframe(table_res, use_container_width=True, height=750, hide_index=True)
    with c2:
        st.subheader("🔮 Simulation")
        with st.container(height=750, border=True):
            for m in api_matches:
                status = m.get('status', {})
                if not status.get('finished') and not status.get('cancelled'):
                    match_time = pd.to_datetime(status.get('utcTime'), errors='coerce')
                    if pd.notnull(match_time) and match_time.date() >= selected_date:
                        h_name, a_name, m_id = m['home']['name'], m['away']['name'], str(m['id'])
                        
                        if sim_mode == "1X2 (Quick)":
                            # 🌟 ZMODYFIKOWANE PROPORCJE - col3 ma rezerwację szerokości
                            col1, col2, col3, col4, col5 = st.columns([0.7, 2.5, 1.8, 2.5, 0.1])
                            with col1: st.caption(match_time.strftime('%d.%m'))
                            with col2: st.markdown(f"<div class='team-label' style='text-align:right; font-weight:bold; padding-top:5px;'>{h_name}</div>", unsafe_allow_html=True)
                            with col3: st.pills("1X2", ["1", "X", "2"], key=f"1x2_{m_id}_{rc}", label_visibility="collapsed")
                            with col4: st.markdown(f"<div class='team-label' style='text-align:left; font-weight:bold; padding-top:5px;'>{a_name}</div>", unsafe_allow_html=True)
                        else:
                            col1, col2, col3, col4, col5, col6 = st.columns([0.7, 2.5, 0.8, 0.8, 2.5, 0.1])
                            with col1: st.caption(match_time.strftime('%d.%m'))
                            with col2: st.markdown(f"<div class='team-label' style='text-align:right; font-weight:bold; padding-top:8px;'>{h_name}</div>", unsafe_allow_html=True)
                            with col3: st.text_input("H", key=f"h_{m_id}_{rc}", label_visibility="collapsed")
                            with col4: st.text_input("A", key=f"a_{m_id}_{rc}", label_visibility="collapsed")
                            with col5: st.markdown(f"<div class='team-label' style='text-align:left; font-weight:bold; padding-top:8px;'>{a_name}</div>", unsafe_allow_html=True)
else:
    st.warning("No data available.")