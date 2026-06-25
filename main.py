import streamlit as st
import itertools
from tinydb import TinyDB, Query

st.set_page_config(
    page_title="🏐 Volleyball Ticker",
    page_icon="🏐",
    layout="centered",
    initial_sidebar_state="collapsed",
)

DB_PATH = "volleyball.json"
db       = TinyDB(DB_PATH)
t_setup  = db.table("setup")
t_spiele = db.table("spiele")
Spiel    = Query()

st.markdown("""
<style>
  .block-container { padding: 1rem 0.5rem; max-width: 480px; margin: auto; }
  h1 { text-align: center; font-size: 1.8rem !important; }
  .score-display { font-size: 3.5rem; font-weight: 900; text-align: center; line-height: 1; margin: 0; }
  div[data-testid="stButton"] button { height: 3.5rem; font-size: 1.4rem; font-weight: bold; border-radius: 10px; width: 100%; }
  .trow { background:#1e2a3a; border-radius:10px; padding:.6rem .9rem; margin-bottom:.4rem; border-left:4px solid #4a9eff; overflow:hidden; }
  .trow .tname { font-size:1rem; font-weight:700; color:#fff; }
  .trow .tpkt  { font-size:1.2rem; font-weight:800; color:#4a9eff; float:right; }
</style>
""", unsafe_allow_html=True)

def get_setup():
    rows = t_setup.all()
    return rows[0] if rows else {}

def save_setup(data):
    t_setup.truncate()
    t_setup.insert(data)

def get_spiele():
    return sorted(t_spiele.all(), key=lambda s: s["nr"])

def save_spiel(spiel):
    t_spiele.upsert(spiel, Spiel.nr == spiel["nr"])

def reset_db():
    t_setup.truncate()
    t_spiele.truncate()

def erstelle_spielplan(teams):
    return [
        {"nr": nr, "heim": a, "gast": b,
         "punkte_heim": 0, "punkte_gast": 0,
         "gespielt": False, "sieger": None}
        for nr, (a, b) in enumerate(itertools.combinations(teams, 2), 1)
    ]

def check_gewonnen(ph, pg, ziel):
    return max(ph, pg) >= ziel and abs(ph - pg) >= 2

st.title("🏐 Volleyball-Live-Ticker")
setup = get_setup()

if not setup:
    st.header("Turnier erstellen")
    zielpunkte = st.radio("Bis wie viele Punkte?", options=[15, 25], format_func=lambda x: f"{x} Punkte")
    teams_text = st.text_area("Mannschaften (eine pro Zeile)", "Team A\nTeam B")
    if st.button("Turnier starten"):
        teams = [t.strip() for t in teams_text.split("\n") if t.strip()]
        if len(teams) < 2:
            st.error("Bitte mindestens 2 Teams eintragen!")
        else:
            save_setup({"zielpunkte": zielpunkte, "teams": teams})
            for s in erstelle_spielplan(teams):
                save_spiel(s)
            st.rerun()

else:
    tabs = st.tabs(["📅 Spielplan", "🏆 Tabelle", "⚙️ Optionen"])
    ziel_pkt = setup["zielpunkte"]

    with tabs[0]:
        st.header("Spielplan")
        st.caption("📱 Handy: bitte Querformat verwenden")
        spiele = get_spiele()

        for s in spiele:
            status = "✅" if s["gespielt"] else "⏳"
            with st.expander(f"{status} Spiel {s['nr']}: {s['heim']} vs. {s['gast']}"):
                if not s["gespielt"]:
                    match_vorbei = check_gewonnen(s["punkte_heim"], s["punkte_gast"], ziel_pkt)
                    st.markdown(f"<p style='text-align:center;color:#888;'>Ziel: {ziel_pkt} Punkte</p>", unsafe_allow_html=True)

                    # Score
                    col_h, col_sep, col_g = st.columns([5, 1, 5])
                    with col_h:
                        st.markdown(f"<p style='text-align:center;font-weight:bold;'>{s['heim']}</p>", unsafe_allow_html=True)
                        st.markdown(f"<p class='score-display'>{s['punkte_heim']}</p>", unsafe_allow_html=True)
                    with col_sep:
                        st.markdown("<p style='text-align:center;font-size:1.5rem;margin-top:2rem;'>:</p>", unsafe_allow_html=True)
                    with col_g:
                        st.markdown(f"<p style='text-align:center;font-weight:bold;'>{s['gast']}</p>", unsafe_allow_html=True)
                        st.markdown(f"<p class='score-display'>{s['punkte_gast']}</p>", unsafe_allow_html=True)

                    # Buttons – flache 4er-Zeile, nur +1 / -1
                    if not match_vorbei:
                        b1, b2, b3, b4 = st.columns(4)
                        if b1.button("-1", key=f"mh_{s['nr']}", disabled=s["punkte_heim"] == 0, use_container_width=True):
                            s["punkte_heim"] -= 1; save_spiel(s); st.rerun()
                        if b2.button("+1", key=f"ph_{s['nr']}", use_container_width=True):
                            s["punkte_heim"] += 1; save_spiel(s); st.rerun()
                        if b3.button("+1", key=f"pg_{s['nr']}", use_container_width=True):
                            s["punkte_gast"] += 1; save_spiel(s); st.rerun()
                        if b4.button("-1", key=f"mg_{s['nr']}", disabled=s["punkte_gast"] == 0, use_container_width=True):
                            s["punkte_gast"] -= 1; save_spiel(s); st.rerun()

                        # Team-Zuordnung unter den Buttons
                        l, r = st.columns(2)
                        l.caption(f"⬅ {s['heim']}")
                        r.caption(f"{s['gast']} ➡")

                    if match_vorbei:
                        sieger = s["heim"] if s["punkte_heim"] > s["punkte_gast"] else s["gast"]
                        st.success(f"🎉 Sieger: **{sieger}**")
                        c1, c2 = st.columns([3, 1])
                        if c1.button("💾 Ergebnis eintragen", type="primary", key=f"fin_{s['nr']}"):
                            s["gespielt"] = True; s["sieger"] = sieger
                            save_spiel(s); st.rerun()
                        if c2.button("↩️", key=f"undo_{s['nr']}"):
                            if s["punkte_heim"] > s["punkte_gast"]: s["punkte_heim"] -= 1
                            else: s["punkte_gast"] -= 1
                            save_spiel(s); st.rerun()
                else:
                    st.success(f"🏆 **{s['sieger']}** gewinnt ({s['punkte_heim']} : {s['punkte_gast']})")

    with tabs[1]:
        st.header("Rangliste")
        spiele = get_spiele()
        tabelle = {t: {"punkte": 0, "siege": 0, "balle": 0} for t in setup["teams"]}
        for s in spiele:
            if s["gespielt"]:
                tabelle[s["heim"]]["balle"] += s["punkte_heim"]
                tabelle[s["gast"]]["balle"]  += s["punkte_gast"]
                if s["sieger"] == s["heim"]:
                    tabelle[s["heim"]]["punkte"] += 3; tabelle[s["heim"]]["siege"] += 1
                else:
                    tabelle[s["gast"]]["punkte"]  += 3; tabelle[s["gast"]]["siege"]  += 1
        sortiert = sorted(tabelle.items(), key=lambda x: (x[1]["punkte"], x[1]["siege"], x[1]["balle"]), reverse=True)
        for rank, (team, d) in enumerate(sortiert, 1):
            st.markdown(
                f'<div class="trow"><span class="tname">{rank}. {team} ({d["siege"]} Siege)</span>'
                f'<span class="tpkt">{d["punkte"]} Pkt</span></div>',
                unsafe_allow_html=True
            )

    with tabs[2]:
        st.header("Optionen")
        if st.button("🔄 Turnier komplett löschen", type="primary"):
            reset_db()
            st.rerun()