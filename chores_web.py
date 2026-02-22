import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import random
import json
from datetime import date, timedelta

# ─── CONFIG ─────────────────────────────────────────────────────────────────────
TEAM_CHORES = ["Clean Rooms", "Tidy Playroom", "Family Clean-up", "Garden Watering"]

ADMIN_PASSWORD = "parent123"  # ← CHANGE THIS!

# ─── Date helpers ───────────────────────────────────────────────────────────────
today = date.today().isoformat()
today_display = date.today().strftime('%A, %d %B %Y')

# ─── Firebase Setup ──────────────────────────────────────────────────────────────
try:
    service_account_str = st.secrets["firebase"]["service_account_json"]
    service_account_info = json.loads(service_account_str)
    cred = credentials.Certificate(service_account_info)

    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://chores-1a1ac-default-rtdb.asia-southeast1.firebasedatabase.app/'
        })
except Exception as e:
    st.error(f"Firebase failed: {str(e)}")
    st.error("Check secrets → firebase → service_account_json")
    st.stop()

ref = db.reference("/chores/ruby_sofia")

# ─── Load / Init Data ────────────────────────────────────────────────────────────
def get_data():
    data = ref.get() or {}
    data.setdefault("kids", ["Ruby", "Sofia"])
    data.setdefault("chores", [
        "Feed dog", "Do dog poo", "Feed cat", "Clean kitty litter",
        "Put away dishes", "Put away clean clothes",
        "Take out rubbish bins", "Wipe kitchen bench"
    ])
    data.setdefault("last_date", None)
    data.setdefault("last_assignments", {})
    data.setdefault("completions", {})
    data.setdefault("streaks", {"Ruby": 0, "Sofia": 0})
    data.setdefault("last_completed_days", {"Ruby": None, "Sofia": None})
    data.setdefault("points", {"Ruby": 0, "Sofia": 0})
    data.setdefault("badges", {"Ruby": [], "Sofia": []})
    data.setdefault("total_chores_completed", {"Ruby": 0, "Sofia": 0})
    data.setdefault("family_all_done_count", 0)
    data.setdefault("daily_completions", {})  # New: track per day for leaderboard

    data.setdefault("rewards", [
        {"points": 50,  "text": "Ice cream treat 🍦"},
        {"points": 100, "text": "Extra screen time 30 min 🎮"},
        {"points": 200, "text": "Movie night pick 🍿"},
        {"points": 300, "text": "Special family outing 🌟"}
    ])

    ref.set(data)
    return data

data = get_data()

# ─── Leaderboard logic ───────────────────────────────────────────────────────────
def get_leaderboard():
    # Today's leaderboard (chores completed today)
    today_compl = data.get("daily_completions", {}).get(today, {"Ruby": 0, "Sofia": 0})
    today_rank = sorted(
        [(kid, today_compl.get(kid, 0), data["points"].get(kid, 0))
         for kid in data["kids"]],
        key=lambda x: (-x[1], -x[2])  # chores desc, then points desc
    )

    # All-time leaderboard (points + badge count)
    all_time_rank = sorted(
        [(kid, data["points"].get(kid, 0), len(data["badges"].get(kid, [])))
         for kid in data["kids"]],
        key=lambda x: (-x[1], -x[2])
    )

    return today_rank, all_time_rank

def update_daily_completions():
    if today not in data.setdefault("daily_completions", {}):
        data["daily_completions"][today] = {"Ruby": 0, "Sofia": 0}

    for kid in data["kids"]:
        done_today = sum(1 for v in completions.get(kid, {}).values() if v)
        data["daily_completions"][today][kid] = done_today

    ref.set(data)

update_daily_completions()

# ─── Reward & Level ──────────────────────────────────────────────────────────────
def get_level(points):
    if points >= 300: return "Level 4 – Superstar 🌟"
    if points >= 200: return "Level 3 – Champion 🏆"
    if points >= 100: return "Level 2 – Rising Hero 🚀"
    return "Level 1 – Starter 🌱"

def get_reward(points):
    rewards = sorted(data.get("rewards", []), key=lambda x: x["points"], reverse=True)
    for r in rewards:
        if points >= r["points"]:
            return r["text"]
    return "Keep going! Next reward soon"

# ─── Badge system (unchanged from previous) ──────────────────────────────────────
# ... (keep your existing BADGES dict and check_and_award_badges function)

# Early defs
assignments = data.get("last_assignments", {})
completions = data.get("completions", {})

# ─── Main UI ─────────────────────────────────────────────────────────────────────
st.title("Ruby & Sofia Chore Manager")
st.subheader(f"Today: {today_display}")

# ─── Leaderboards (visible to everyone) ──────────────────────────────────────────
st.markdown("### 🏆 Leaderboards")

today_rank, all_time_rank = get_leaderboard()

col_today, col_all = st.columns(2)

with col_today:
    st.subheader("Today's Race")
    for rank, (kid, chores_done, pts) in enumerate(today_rank, 1):
        medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."
        st.markdown(f"{medal} **{kid}** – {chores_done} chores done")

with col_all:
    st.subheader("All-Time Champions")
    for rank, (kid, pts, badge_count) in enumerate(all_time_rank, 1):
        medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."
        st.markdown(f"{medal} **{kid}** – {pts} points • {badge_count} badges")

# ─── Rest of the UI (admin / kid view) remains the same ──────────────────────────
# ... (paste your existing admin and kid view code here, including checkbox loop)

# ─── Progress section (add leaderboard note if needed) ───────────────────────────
st.markdown("### Progress & Rewards")
for kid in data["kids"]:
    p = data["points"].get(kid, 0)
    s = data["streaks"].get(kid, 0)
    lvl = get_level(p)
    badges = data["badges"].get(kid, [])

    st.markdown(f"**{kid}** · {lvl}")
    st.markdown(f"🔥 Streak: **{s}** • ⭐ Points: **{p}**")
    st.progress(min(p / 400, 1.0), text=f"Next: {get_reward(p)}")  # extended to 400 for level 4 feel

    if badges:
        st.markdown("**Badges**")
        cols = st.columns(len(badges))
        for i, b in enumerate(badges):
            cols[i].markdown(f"**{BADGES[b]['icon']}** {b}")

    st.markdown("---")

# ─── Celebration ─────────────────────────────────────────────────────────────────
# ... (keep your existing celebration code)

st.caption("Flynnchilada • Firebase • Add to home screen")