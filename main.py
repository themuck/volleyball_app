import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# Seiteneinstellungen
st.set_page_config(page_title="Heidbrede Volleyball Zähler", page_icon="🏐", layout="centered")

# --- DATENBANK EINRICHTEN ---
DB_FILE = "volleyball.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Tabelle für Spieler
    c.execute('''CREATE TABLE IF NOT EXISTS spieler 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, team TEXT, name TEXT)''')
    # Tabelle für Spiele-Historie
    c.execute('''CREATE TABLE IF NOT EXISTS historie 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, zeitpunkt TEXT, team_a TEXT, team_b TEXT, saetze_a INTEGER, saetze_b INTEGER)''')
    conn.commit()
    conn.close()

init_db()

# --- FUNKTIONEN FÜR DIE DATENBANK ---
def spieler_hinzufuegen(team, name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO spieler (team, name) VALUES (?, ?)", (team, name))
    conn.commit()
    conn.close()

def hole_spieler(team):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT name FROM spieler WHERE team = ?", conn, params=(team,))
    conn.close()
    return df["name"].tolist()

def loesche_spieler(team, name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM spieler WHERE team = ? AND name = ?", (team, name))
    conn.commit()
    conn.close()

def spiel_speichern(team_a, team_b, sätze_a, sätze_b):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    zeit = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute("INSERT INTO historie (zeitpunkt, team_a, team_b, saetze_a, saetze_b) VALUES (?, ?, ?, ?, ?)",
              (zeit, team_a, team_b, sätze_a, sätze_b))
    conn.commit()
    conn.close()

def hole_historie():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT zeitpunkt AS 'Zeitpunkt', team_a AS 'Team A', team_b AS 'Team B', saetze_a AS 'Sätze A', saetze_b AS 'Sätze B' FROM historie", conn)
    conn.close()
    return df

# --- SESSION STATE FÜR DIE APP ---
if 'score_a' not in st.session_state: st.session_state.score_a = 0
if 'score_b' not in st.session_state: st.session_state.score_b = 0
if 'sets_a' not in st.session_state: st.session_state.sets_a = 0
if 'sets_b' not in st.session_state: st.session_state.sets_b = 0
if 'swapped' not in st.session_state: st.session_state.swapped = False
if 'match_over' not in st.session_state: st.session_state.match_over = False
# Merkt sich, ob die Seiten zu Beginn des aktuellen Satzes getauscht waren
# (damit der automatische Wechsel im 5. Satz bei 8 Punkten nur einmal passiert)
if 'fifth_set_switched' not in st.session_state: st.session_state.fifth_set_switched = False

# --- UI: SEITENLEISTE (EINSTELLUNGEN & DATENBANK) ---
st.sidebar.title("⚙️ Verwaltung")

# Teamnamen festlegen
team_a_name = st.sidebar.text_input("Name Team A", value="Team A")
team_b_name = st.sidebar.text_input("Name Team B", value="Team B")

st.sidebar.divider()
st.sidebar.subheader("👤 Spieler hinzufügen")
neuer_spieler = st.sidebar.text_input("Name des Spielers")
ziel_team = st.sidebar.selectbox("Zu welchem Team?", [team_a_name, team_b_name])

if st.sidebar.button("Spieler speichern"):
    if neuer_spieler:
        spieler_hinzufuegen(ziel_team, neuer_spieler)
        st.sidebar.success(f"{neuer_spieler} zu {ziel_team} hinzugefügt!")
        st.rerun()

# --- HAUPTBEREICH: VOLLEYBALL ZÄHLER ---
st.title("🏐 heidbrede Volleyball Zähler")

# Ist es der 5. Satz? (Sätze 0-basiert gezählt, 5. Satz = insgesamt 4 Sätze gespielt)
def ist_fuenfter_satz():
    return st.session_state.sets_a == 2 and st.session_state.sets_b == 2

# Hilfsfunktion für Satz-Gewinn
def check_set_win():
    target = 15 if ist_fuenfter_satz() else 25
    set_gewonnen = False

    if st.session_state.score_a >= target and (st.session_state.score_a - st.session_state.score_b) >= 2:
        st.session_state.sets_a += 1
        st.session_state.score_a, st.session_state.score_b = 0, 0
        set_gewonnen = True
        st.toast(f"🎉 {team_a_name} gewinnt den Satz!")
    elif st.session_state.score_b >= target and (st.session_state.score_b - st.session_state.score_a) >= 2:
        st.session_state.sets_b += 1
        st.session_state.score_a, st.session_state.score_b = 0, 0
        set_gewonnen = True
        st.toast(f"🎉 {team_b_name} gewinnt den Satz!")

    if set_gewonnen:
        # Match gewonnen? (Best of 5 → erste Mannschaft mit 3 Sätzen)
        if st.session_state.sets_a >= 3:
            st.session_state.match_over = True
            st.toast(f"🏆 {team_a_name} gewinnt das Spiel!")
        elif st.session_state.sets_b >= 3:
            st.session_state.match_over = True
            st.toast(f"🏆 {team_b_name} gewinnt das Spiel!")
        else:
            # Automatischer Seitenwechsel nach jedem Satz
            st.session_state.swapped = not st.session_state.swapped
            st.session_state.fifth_set_switched = False

# Automatischer Seitenwechsel im 5. Satz bei 8 Punkten
def check_fifth_set_switch():
    if ist_fuenfter_satz() and not st.session_state.fifth_set_switched:
        total_points = st.session_state.score_a + st.session_state.score_b
        # Wechsel wenn ein Team 8 Punkte erreicht (= führendes Team hat 8)
        if st.session_state.score_a >= 8 or st.session_state.score_b >= 8:
            st.session_state.swapped = not st.session_state.swapped
            st.session_state.fifth_set_switched = True
            st.toast("🔄 Automatischer Seitenwechsel im 5. Satz!")

# Sätze-Anzeige (respektiert Seitenwechsel)
if not st.session_state.swapped:
    saetze_links, saetze_rechts = st.session_state.sets_a, st.session_state.sets_b
    name_links, name_rechts = team_a_name, team_b_name
else:
    saetze_links, saetze_rechts = st.session_state.sets_b, st.session_state.sets_a
    name_links, name_rechts = team_b_name, team_a_name

st.markdown(f"### 🏆 Sätze: {name_links} `{saetze_links}` : `{saetze_rechts}` {name_rechts}")

# Match-Gewinner anzeigen
if st.session_state.match_over:
    if st.session_state.sets_a >= 3:
        st.success(f"🏆 **{team_a_name}** hat das Spiel gewonnen! ({st.session_state.sets_a}:{st.session_state.sets_b})")
    else:
        st.success(f"🏆 **{team_b_name}** hat das Spiel gewonnen! ({st.session_state.sets_b}:{st.session_state.sets_a})")

st.divider()

# Teams anzeigen (mit Seitenwechsel)
col1, col2 = st.columns(2)
if not st.session_state.swapped:
    t1, t2 = team_a_name, team_b_name
    s1, s2 = st.session_state.score_a, st.session_state.score_b
    id1, id2 = "a", "b"
else:
    t1, t2 = team_b_name, team_a_name
    s1, s2 = st.session_state.score_b, st.session_state.score_a
    id1, id2 = "b", "a"

# Punkte-Buttons nur aktiv wenn Spiel nicht vorbei
buttons_disabled = st.session_state.match_over

# Spalte Links
with col1:
    st.header(t1)
    # Spieler aus der DB unter dem Teamnamen anzeigen
    spieler_liste_1 = hole_spieler(t1)
    if spieler_liste_1:
        st.caption("👥 Aufstellung: " + ", ".join(spieler_liste_1))
    
    st.metric(label="Punkte", value=s1)
    if st.button(f"➕ Punkt {t1}", key="p_l", disabled=buttons_disabled):
        if id1 == "a": st.session_state.score_a += 1
        else: st.session_state.score_b += 1
        check_fifth_set_switch()
        check_set_win()
        st.rerun()
    if st.button(f"➖ Abzug {t1}", key="m_l", disabled=buttons_disabled):
        if id1 == "a" and st.session_state.score_a > 0: st.session_state.score_a -= 1
        elif id1 == "b" and st.session_state.score_b > 0: st.session_state.score_b -= 1
        st.rerun()

# Spalte Rechts
with col2:
    st.header(t2)
    spieler_liste_2 = hole_spieler(t2)
    if spieler_liste_2:
        st.caption("👥 Aufstellung: " + ", ".join(spieler_liste_2))
        
    st.metric(label="Punkte", value=s2)
    if st.button(f"➕ Punkt {t2}", key="p_r", disabled=buttons_disabled):
        if id2 == "a": st.session_state.score_a += 1
        else: st.session_state.score_b += 1
        check_fifth_set_switch()
        check_set_win()
        st.rerun()
    if st.button(f"➖ Abzug {t2}", key="m_r", disabled=buttons_disabled):
        if id2 == "a" and st.session_state.score_a > 0: st.session_state.score_a -= 1
        elif id2 == "b" and st.session_state.score_b > 0: st.session_state.score_b -= 1
        st.rerun()

st.divider()

# Steuerung
c1, c2, c3 = st.columns(3)
with c1:
    if st.button("🔄 Seitenwechsel", width="stretch"):
        st.session_state.swapped = not st.session_state.swapped
        st.rerun()
with c2:
    if st.button("💾 Spiel speichern", width="stretch"):
        spiel_speichern(team_a_name, team_b_name, st.session_state.sets_a, st.session_state.sets_b)
        st.success("Spiel in Datenbank gespeichert!")
with c3:
    if st.button("❌ Reset", type="primary", width="stretch"):
        st.session_state.score_a = 0
        st.session_state.score_b = 0
        st.session_state.sets_a = 0
        st.session_state.sets_b = 0
        st.session_state.swapped = False
        st.session_state.match_over = False
        st.session_state.fifth_set_switched = False
        st.rerun()

# --- HISTORIE AUS DER DB ANZEIGEN ---
st.divider()
st.subheader("📊 Spielhistorie (aus der Datenbank)")
df_h = hole_historie()
if not df_h.empty:
    st.dataframe(df_h, width="stretch")
else:
    st.info("Noch keine Spiele in der Datenbank.")

# --- BONUS: SPIELER LÖSCHEN OPTION ---
st.sidebar.divider()
st.sidebar.subheader("🗑️ Spieler löschen")
team_auswahl = st.sidebar.selectbox("Team wählen", [team_a_name, team_b_name], key="del_team")
spieler_auswahl = st.sidebar.selectbox("Spieler wählen", hole_spieler(team_auswahl) if team_auswahl else [])
if st.sidebar.button("Spieler entfernen"):
    if spieler_auswahl:
        loesche_spieler(team_auswahl, spieler_auswahl)
        st.sidebar.warning(f"{spieler_auswahl} wurde gelöscht.")
        st.rerun()
