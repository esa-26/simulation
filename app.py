import streamlit as st
import pandas as pd
import requests
import smtplib
import urllib.parse
from datetime import datetime
from email.mime.text import MIMEText
import streamlit.components.v1 as components

# ----------------- 1. GOOGLE ANALYTICS INTEGRACJA -----------------
GA_ID = "G-S0HCG6VSHG" 

# Ten blok kodu sprawia, że każde wejście na stronę jest odnotowane w Twoim panelu GA4
components.html(
    f"""
    <script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());
      gtag('config', '{GA_ID}');
    </script>
    """,
    height=0,
)

# ----------------- FUNKCJE POMOCNICZE -----------------
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
    except Exception: return False

# ----------------- KONFIGURACJA STRONY -----------------
st.set_page_config(page_title="FlashCalc - Fast League Simulator", page_icon="⚡", layout="wide")

# ----------------- CSS: SMART-STACK DESIGN -----------------
st.markdown("""
<style>
    [data-testid="stHorizontalBlock"] { align-items: center !important; gap: 0px !important; }
    .match-row-container { padding: 6px 0 !important; border-bottom: 1px solid #f2f2f2 !important; width: 100% !important; }
    .teams-inline-container { display: flex !important; align-items: center !important; gap: 8px !important; overflow: hidden !important; }
    .team-name { font-size: 14px !important; font-weight: 700 !important; white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important; flex: 0 1 auto !important; }
    .vs-divider { font-size: 11px !important; color: #bbb !important; flex: 0 0 auto !important; }
    .main-title { color: #ee4444; font-size: 42px; font-weight: 800; margin-bottom: -10px; }
    
    /* Social Buttons Styling */
    .share-btn {
        display: inline-flex; align-items: center; padding: 8px 16px; border-radius: 20px;
        text-decoration: none; color: white !important; font-size: 13px; font-weight: bold; margin-right: 8px;
    }
    
    @media (max-width: 768px) {
        .main-container [data-testid="stHorizontalBlock"] { flex-direction: column !important; }
        .teams-inline-container { justify-content: center !important; margin-bottom: 8px !important; }
        .inputs-wrap-mobile { display: flex !important; justify-content: center !important; width: 100% !important; }
    }
    
    [data-testid="stBaseButton-pills"] { border-radius: 4px !important; padding: 2px 12px !important; font-weight: bold !important; border: 1px solid #d1d5db !important; }
    [data-testid="stBaseButton-pills"][aria-selected="true"] { background-color: #ee4444 !important; color: white !important; border-color: #ee4444 !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='main-title'>⚡ FlashCalc</div>", unsafe_allow_html=True)
st.caption("Standings at the speed of light. Predict, Simulate, Share.")

# ----------------- LEAGUE MAPPING (RapidAPI ID) -----------------
LEAGUES = {
    "Poland: Ekstraklasa": 202,
    "Poland: Betclic 1. Liga": 229,
    "England: Premier League": 47,
    "Spain: La Liga": 87,
    "Germany: Bundesliga": 54,
    "Italy: Serie A": 55,
    "France: Ligue 1": 53
}

# ----------------- LOGIKA URL (PARAMETRY) -----------------
query_params = st.query_params
if 'reset_counter' not in st.session_state:
    st.session_state.reset_counter = 0

# ----------------- SIDEBAR -----------------
st.sidebar.header("🏆 Competitions")
# Jeśli link zawiera lid, ustaw go jako domyślny
default_ix = 0
if "lid" in query_params:
    try:
        lid_val = int(query_params["lid"])
        default_ix = list(LEAGUES.values()).index(lid_val)
    except: pass

selected_league_name = st.sidebar.selectbox("Select League:", list(LEAGUES.keys()), index=default_ix)
league_id = LEAGUES[selected_league_name]

st.sidebar.divider()
if st.sidebar.button("🗑️ Reset All", use_container_width=True):
    st.session_state.reset_counter += 1
    st.query_params.clear()
    st.rerun()

st.sidebar.link_button("❤️ Support FlashCalc", "https://buymeacoffee.com/flashcalc1w", use_container_width=True)

# ----------------- DATA FETCHING -----------------
@st.cache_data(ttl=86400)
def fetch_api_data(lid):
    url = f"https://free-api-live-football-data.p.rapidapi.com/football-get-all-matches-by-league?leagueid={lid}"
    headers = {"x-rapidapi-host": "free-api-live-football-data.p.rapidapi.com", "x-rapidapi-key": st.secrets["RAPIDAPI_KEY"]}
    try: return requests.get(url, headers=headers).json()
    except: return {}

data_json = fetch_api_data(league_id)
api_matches = data_json.get("response", {}).get("matches", [])

# ----------------- SIMULATION LOGIC (Session + URL) -----------------
active_simulations = {}
rc = st.session_state.reset_counter

# Najpierw wczytaj z URL
for key, value in query_params.items():
    if key.startswith("m"):
        m_id = key[1:]
        if value == "1": active_simulations[m_id] = {'h': 1, 'a': 0}
        elif value == "X": active_simulations[m_id] = {'h': 0, 'a': 0}
        elif value == "2": active_simulations[m_id] = {'h': 0, 'a': 1}

# Potem nadpisz tym co klika użytkownik w tej sesji
for key, val in st.session_state.items():
    if key.endswith(f'_{rc}'):
        m_id = key.split('_')[1]
        if key.startswith('1x2_') and val in ["1", "X", "2"]:
            if val == "1": active_simulations[m_id] = {'h': 1, 'a': 0}
            elif val == "X": active_simulations[m_id] = {'h': 0, 'a': 0}
            elif val == "2": active_simulations[m_id] = {'h': 0, 'a': 1}

# ----------------- GENEROWANIE LINKU -----------------
def get_share_url(sims, lid):
    params = {"lid": lid}
    for m_id, res in sims.items():
        val = "1" if res['h'] > res['a'] else ("X" if res['h'] == res['a'] else "2")
        params[f"m{m_id}"] = val
    return "https://flashcalc.streamlit.app/?" + urllib.parse.urlencode(params)

# ----------------- STANDINGS ENGINE -----------------
def generate_table(matches_list, date_limit, sym, lid):
    stats = {}
    for m in matches_list:
        m_id = str(m.get('id', ''))
        st_obj = m.get('status', {})
        m_date = pd.to_datetime(st_obj.get('utcTime'), errors='coerce')
        gh, ga = None, None
        if m_id in sym: gh, ga = sym[m_id]['h'], sym[m_id]['a']
        elif m_date and m_date.date() <= date_limit and st_obj.get('finished'):
            gh, ga = m.get('home', {}).get('score'), m.get('away', {}).get('score')
        
        if gh is not None and ga is not None:
            for team, s, c in [(m['home']['name'], gh, ga), (m['away']['name'], ga, gh)]:
                if team not in stats: stats[team] = {'P': 0, 'Pts': 0, 'diff': 0}
                stats[team]['P']+=1
                stats[team]['diff']+=(s-c)
                if s > c: stats[team]['Pts'] += 3
                elif s == c: stats[team]['Pts'] += 1

    if lid == 202: # Ekstraklasa Penalty
        for t in stats:
            if "Lechia" in t: stats[t]['Pts'] -= 5

    df = pd.DataFrame.from_dict(stats, orient='index').reset_index()
    if not df.empty:
        df.rename(columns={'index': 'Team'}, inplace=True)
        df = df.sort_values(by=['Pts', 'diff'], ascending=False).reset_index(drop=True)
        df.index += 1
        return df[['Team', 'P', 'Pts', 'diff']]
    return pd.DataFrame()

# ----------------- MAIN VIEW -----------------
c1, c2 = st.columns([1.4, 1.2])

with c1:
    st.subheader("📊 Standings")
    table = generate_table(api_matches, datetime.now().date(), active_simulations, league_id)
    st.dataframe(table, use_container_width=True, hide_index=True)

with c2:
    st.subheader("🔮 Simulation Hub")
    
    # SHARE SECTION
    if active_simulations:
        s_url = get_share_url(active_simulations, league_id)
        st.info("🔗 Share this scenario:")
        st.markdown(f"""
        <a href="https://twitter.com/intent/tweet?text=Check%20my%20league%20simulation!&url={s_url}" class="share-btn" style="background:#1DA1F2">Twitter / X</a>
        <a href="https://api.whatsapp.com/send?text=My%20Prediction:%20{s_url}" class="share-btn" style="background:#25D366">WhatsApp</a>
        """, unsafe_allow_html=True)
        st.text_input("Direct Link:", s_url)

    with st.container(height=650, border=True):
        for m in api_matches:
            status = m.get('status', {})
            m_time = pd.to_datetime(status.get('utcTime'), errors='coerce')
            if not status.get('finished') and m_time:
                h_n, a_n, m_id = m['home']['name'], m['away']['name'], str(m['id'])
                st.markdown(f"<div class='match-row-container'>", unsafe_allow_html=True)
                cl, cr = st.columns([3, 2])
                with cl:
                    st.markdown(f"<div class='teams-inline-container'><span style='color:#888; font-size:11px; margin-right:5px;'>{m_time.strftime('%d.%m')}</span><span class='team-name'>{h_n}</span><span class='vs-divider'>vs</span><span class='team-name'>{a_n}</span></div>", unsafe_allow_html=True)
                with cr:
                    # Domyślna wartość z URL
                    def_val = None
                    if m_id in active_simulations:
                        res = active_simulations[m_id]
                        def_val = "1" if res['h'] > res['a'] else ("X" if res['h'] == res['a'] else "2")
                    
                    st.pills("1X2", ["1", "X", "2"], key=f"1x2_{m_id}_{rc}", label_visibility="collapsed", default=def_val)
                st.markdown("</div>", unsafe_allow_html=True)