import streamlit as st
import pandas as pd
import requests
import smtplib
from datetime import datetime
from email.mime.text import MIMEText

# ----------------- FUNKCJA WYSYŁANIA MAILA -----------------
def send_email(user_msg, user_contact):
    msg_content = f"New message from FlashCalc user!\n\nContact: {user_contact}\n\nMessage:\n{user_msg}"
    msg = MIMEText(msg_content)
    msg['Subject'] = "⚡ FlashCalc Feedback"
    msg['From'] = st.secrets["EMAIL_USER"]
    msg['To'] = "flashcalc1x2@gmail.com"
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(st.secrets["EMAIL_USER"], st.secrets["EMAIL_PASS"])
            server.send_message(msg)
        return True
    except Exception:
        return False

# ----------------- KONFIGURACJA STRONY -----------------
st.set_page_config(page_title="FlashCalc - Fast League Simulator", page_icon="⚡", layout="wide")

# ----------------- CSS: ADVANCED CONDENSED DESIGN -----------------
st.markdown("""
<style>
    /* Główne kontenery */
    [data-testid="stHorizontalBlock"] { align-items: center !important; gap: 0px !important; }
    
    /* --- DESKTOP ONLY (Zagęszczenie) --- */
    @media (min-width: 769px) {
        .match-row-container {
            padding: 4px 0 !important; /* Minimalny odstęp między meczami */
            border-bottom: 1px solid #f7f7f7 !important;
        }
        /* Sprawienie, by kolumny Streamlit były bardziej zbite */
        div[data-testid="column"] {
            padding: 0 5px !important;
        }
        .team-name-desktop {
            font-size: 14px !important;
            font-weight: 600 !important;
        }
    }

    /* --- MOBILE ONLY --- */
    @media (max-width: 768px) {
        .main-container [data-testid="stHorizontalBlock"] {
            flex-direction: column !important;
        }
        .match-row-container {
            padding: 12px 0 !important;
            border-bottom: 1px solid #f2f2f2 !important;
            width: 100% !important;
        }
        .teams-one-line {
            display: flex !important;
            flex-direction: row !important;
            justify-content: center !important;
            align-items: center !important;
            gap: 6px !important;
            width: 100% !important;
            margin-bottom: 8px !important;
        }
        .team-name {
            font-size: 13px !important;
            font-weight: 700 !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            flex: 1 1 auto !important;
            max-width: 42% !important;
        }
        .team-name-left { text-align: right !important; }
        .team-name-right { text-align: left !important; }
        .vs-divider { font-size: 10px !important; color: #ccc !important; }
    }

    /* Kafelki 1 X 2 i Inputy */
    [data-testid="stBaseButton-pills"] { 
        border-radius: 4px !important; padding: 2px 10px !important; font-weight: bold !important; 
    }
    [data-testid="stBaseButton-pills"][aria-selected="true"] {
        background-color: #ee4444 !important; color: white !important; border-color: #ee4444 !important;
    }
    div[data-testid="stTextInput"] input { 
        text-align: center !important; font-size: 16px !important; font-weight: bold !important; height: 32px !important;
    }
    .main-title { color: #ee4444; font-size: 42px; font-weight: 800; margin-bottom: -10px; }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='main-title'>⚡ FlashCalc</div>", unsafe_allow_html=True)
st.caption("Standings at the speed of light. Predict titles, avoid the drop.")

if 'reset_counter' not in st.session_state:
    st.session_state.reset_counter = 0

# ----------------- LEAGUE MAPPING -----------------
LEAGUES = {
    "England: Premier League": 47, "Poland: Ekstraklasa": 196, "Spain: La Liga": 87,
    "Germany: Bundesliga": 54, "Italy: Serie A": 55, "France: Ligue 1": 53,
    "Netherlands: Eredivisie": 57, "Portugal: Primeira Liga": 61, "England: Championship": 48,
    "Turkey: Süper Lig": 71, "Belgium: Pro League": 51, "Scotland: Premiership": 64
}

# ----------------- SIDEBAR -----------------
st.sidebar.header("🏆 Competitions")
selected_league_name = st.sidebar.selectbox("Select League:", list(LEAGUES.keys()))
league_id = LEAGUES[selected_league_name]

st.sidebar.divider()
st.sidebar.header("⚙️ Simulation Settings")
selected_date = st.sidebar.date_input("Standings as of:", datetime.now().date())
sim_mode = st.sidebar.radio("🕹️ Input Mode:", ["1X2 (Fast)", "Exact Score"])
table_type = st.sidebar.radio("🔍 View:", ["All Games", "Home", "Away"])
form_limit = st.sidebar.number_input("Last X Matches Only:", min_value=0, max_value=38, value=0)

if st.sidebar.button("🗑️ Reset FlashCalc", use_container_width=True):
    st.session_state.reset_counter += 1
    st.cache_data.clear()
    st.rerun()

st.sidebar.divider()
st.sidebar.header("☕ Support")
st.sidebar.link_button("❤️ Support FlashCalc", "https://buymeacoffee.com/flashcalc1w", use_container_width=True)

with st.sidebar.expander("📬 Contact"):
    with st.form("contact_form", clear_on_submit=True):
        u_nick = st.text_input("Nick/Email:")
        u_msg = st.text_area("Message:")
        if st.form_submit_button("Send", use_container_width=True):
            if u_msg.strip() and send_email(u_msg, u_nick): st.success("Sent! ⚡")

# ----------------- DATA FETCHING (TTL 24H) -----------------
@st.cache_data(ttl=86400)
def fetch_api_data(lid):
    url = f"https://free-api-live-football-data.p.rapidapi.com/football-get-all-matches-by-league?leagueid={lid}"
    headers = {"x-rapidapi-host": "free-api-live-football-data.p.rapidapi.com", "x-rapidapi-key": st.secrets["RAPIDAPI_KEY"]}
    try:
        response = requests.get(url, headers=headers)
        return response.json()
    except Exception: return {}

data_json = fetch_api_data(league_id)
api_matches = data_json.get("response", {}).get("matches", [])

# ----------------- SIMULATION LOGIC -----------------
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
    stats = {}; processed = []
    for m in matches_list:
        m_id = str(m.get('id', ''))
        st_obj = m.get('status', {})
        if not st_obj.get('utcTime'): continue
        m_date = pd.to_datetime(st_obj['utcTime'], errors='coerce')
        gh, ga = None, None
        if m_id in sym: gh, ga = sym[m_id]['h'], sym[m_id]['a']
        elif m_date.date() <= date_limit and st_obj.get('finished'):
            gh, ga = m.get('home', {}).get('score'), m.get('away', {}).get('score')
        if gh is not None and ga is not None:
            processed.append({'d': m_date, 'h': m['home']['name'], 'a': m['away']['name'], 'gh': gh, 'ga': ga})
    processed.sort(key=lambda x: x['d'], reverse=True)
    def add_stats(team, g_s, g_c):
        if team not in stats: stats[team] = {'P': 0, 'Pts': 0, 'W': 0, 'D': 0, 'L': 0, 'GS': 0, 'GC': 0, 'History': []}
        if f_limit > 0 and stats[team]['P'] >= f_limit: return
        stats[team]['P']+=1; stats[team]['GS']+=g_s; stats[team]['GC']+=g_c
        if g_s > g_c: stats[team]['Pts'] += 3; stats[team]['W'] += 1; stats[team]['History'].append('W')
        elif g_s == g_c: stats[team]['Pts'] += 1; stats[team]['D'] += 1; stats[team]['History'].append('D')
        else: stats[team]['L'] += 1; stats[team]['History'].append('L')
    for m in processed:
        if t_type in ["All Games", "Home"]: add_stats(m['h'], m['gh'], m['ga'])
        if t_type in ["All Games", "Away"]: add_stats(m['a'], m['ga'], m['gh'])
    df = pd.DataFrame.from_dict(stats, orient='index').reset_index()
    if not df.empty:
        df.rename(columns={'index': 'Team'}, inplace=True); df['Goals'] = df['GS'].astype(str) + '-' + df['GC'].astype(str)
        df['W-D-L'] = df['W'].astype(str) + '-' + df['D'].astype(str) + '-' + df['L'].astype(str)
        df['Form'] = df['History'].apply(lambda x: "".join(x[:5])); df['diff'] = df['GS'] - df['GC']
        df = df.sort_values(by=['Pts', 'diff', 'GS'], ascending=[False, False, False]).reset_index(drop=True)
        df.index = range(1, len(df) + 1); df.index.name = 'Pos'; df = df.reset_index()
        df = df[['Pos', 'Team', 'P', 'Pts', 'Goals', 'W-D-L', 'Form']]
    return df

def highlight_zones(res_df):
    num_teams = len(res_df)
    def apply_color(row):
        color = ''
        if row['Pos'] == 1: color = 'background-color: #fff4f4; color: #ee4444; font-weight: bold; border-left: 4px solid #ee4444;'
        elif row['Pos'] > num_teams - 3: color = 'background-color: #f9fafb; color: #6b7280; border-left: 4px solid #9ca3af;'
        return [color] * len(row)
    return res_df.style.apply(apply_color, axis=1)

# ----------------- MAIN VIEW -----------------
if api_matches:
    st.markdown("<div class='main-container'>", unsafe_allow_html=True)
    c1, c2 = st.columns([1.5, 1.2])
    with c1:
        st.subheader("📊 Live Standings")
        table_data = generate_table(api_matches, selected_date, active_simulations, table_type, form_limit)
        if not table_data.empty: st.dataframe(highlight_zones(table_data), use_container_width=True, height=750, hide_index=True)
    with c2:
        st.subheader("🔮 Simulation Hub")
        with st.container(height=750, border=True):
            for m in api_matches:
                status = m.get('status', {})
                if not status.get('finished') and not status.get('cancelled'):
                    m_time = pd.to_datetime(status.get('utcTime'), errors='coerce')
                    if pd.notnull(m_time) and m_time.date() >= selected_date:
                        h_n, a_n, m_id = m['home']['name'], m['away']['name'], str(m['id'])
                        
                        st.markdown("<div class='match-row-container'>", unsafe_allow_html=True)
                        
                        # --- DETEKCJA URZĄDZENIA PRZEZ KOLUMNY (Streamlit automatycznie stackuje na mobile) ---
                        if sim_mode == "1X2 (Fast)":
                            # Desktop: [Data | Home vs Away | Pills]
                            col_a, col_b, col_c = st.columns([0.6, 3, 1.4])
                            with col_a: st.caption(m_time.strftime('%d.%m'))
                            with col_b: st.markdown(f"<div class='teams-one-line'><div class='team-name team-name-left'>{h_n}</div><div class='vs-divider'>vs</div><div class='team-name team-name-right'>{a_n}</div></div>", unsafe_allow_html=True)
                            with col_c: st.pills("1X2", ["1", "X", "2"], key=f"1x2_{m_id}_{rc}", label_visibility="collapsed")
                        else:
                            # Desktop: [Data | Home vs Away | Score H | Score A]
                            col_a, col_b, col_c, col_d = st.columns([0.6, 2.5, 0.7, 0.7])
                            with col_a: st.caption(m_time.strftime('%d.%m'))
                            with col_b: st.markdown(f"<div class='teams-one-line'><div class='team-name team-name-left'>{h_n}</div><div class='vs-divider'>vs</div><div class='team-name team-name-right'>{a_n}</div></div>", unsafe_allow_html=True)
                            with col_c: st.text_input("H", key=f"h_{m_id}_{rc}", label_visibility="collapsed", placeholder="H")
                            with col_d: st.text_input("A", key=f"a_{m_id}_{rc}", label_visibility="collapsed", placeholder="A")
                        
                        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
else:
    st.warning("No data available.")