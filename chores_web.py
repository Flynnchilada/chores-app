# ─── IMPORTS (MUST BE FIRST) ─────────────────────────────────────────────
import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import json
from datetime import date

# ─── CONFIG ─────────────────────────────────────────────────────────────
TEAM_CHORES = ["Clean Rooms", "Tidy Playroom", "Family Clean-up", "Garden Watering"]
ADMIN_PASSWORD = "parent123"  # CHANGE THIS

today = date.today().isoformat()
today_display = date.today().strftime('%A, %d %B %Y')

# ─── Firebase Setup ─────────────────────────────────────────────────────
try:
    service_account_str = st.secrets["firebase"]["service_account_json"]
    service_account_info = json.loads(service_account_str)
    cred = credentials.Certificate(service_account_info)

    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred, {
            "databaseURL": "https://chores-1a1ac-default-rtdb.asia-southeast1.firebasedatabase.app/"
        })
except Exception as e:
    st.error(f"Firebase failed: {e}")
    st.stop()

ref = db.reference("/chores/ruby_sofia")

# ─── Load / Init Data ────────────────────────────────────────────────────
def get_data():
    data = ref.get() or {}

    data.setdefault("kids", ["Ruby", "Sofia"])
    data.setdefault("chores", [
        "Feed dog", "Do dog poo", "Feed cat", "Clean kitty litter",
        "Put away dishes", "Put away clean clothes",
        "Take out rubbish bins", "Wipe kitchen bench"
    ])
    data.setdefault("last_assignments", {})
    data.setdefault("completions", {})
    data.setdefault("streaks", {"Ruby": 0, "Sofia": 0})
    data.setdefault("points", {"Ruby": 0, "Sofia": 0})
    data.setdefault("badges", {"Ruby": [], "Sofia": []})
    data.setdefault("total_chores_completed", {"Ruby": 0, "Sofia": 0})
    data.setdefault("family_all_done_count", 0)
    data.setdefault("daily_completions", {})

    data.setdefault("rewards", [
        {"points": 50,  "text": "Ice cream treat 🍦"},
        {"points": 100, "text": "Extra screen time 30 min 🎮"},
        {"points": 200, "text": "Movie night pick 🍿"},
        {"points": 300, "text": "Special family outing 🌟"}
    ])

    ref.set(data)
    return data

data = get_data()
assignments = data.get("last_assignments", {})

# ─── Leaderboard Logic ───────────────────────────────────────────────────
def get_leaderboard():
    today_compl = data.get("daily_completions", {}).get(
        today, {"Ruby": 0, "Sofia": 0}
    )

    today_rank = sorted(
        [(kid, today_compl.get(kid, 0), data["points"].get(kid, 0))
         for kid in data["kids"]],
        key=lambda x: (-x[1], -x[2])
    )

    all_time_rank = sorted(
        [(kid, data["points"].get(kid, 0), len(data["badges"].get(kid, [])))
         for kid in data["kids"]],
        key=lambda x: (-x[1], -x[2])
    )

    return today_rank, all_time_rank

# ─── Rewards / Levels ────────────────────────────────────────────────────
def get_level(points):
    if points >= 300: return "Level 4 – Superstar 🌟"
    if points >= 200: return "Level 3 – Champion 🏆"
    if points >= 100: return "Level 2 – Rising Hero 🚀"
    return "Level 1 – Starter 🌱"

def get_reward(points):
    for r in sorted(data["rewards"], key=lambda x: x["points"], reverse=True):
        if points >= r["points"]:
            return r["text"]
    return "Keep going! Next reward soon"

# ─── Chore Checkbox Logic ────────────────────────────────────────────────
def on_chore_change(kid, chore, key):
    new_value = st.session_state.get(key, False)
    old_value = data.get("completions", {}).get(kid, {}).get(chore, False)

    data.setdefault("completions", {}).setdefault(kid, {})
    data["completions"][kid][chore] = new_value

    if new_value and not old_value:
        data["points"][kid] += 10
        data["total_chores_completed"][kid] += 1
        st.toast(f"+10 points for {kid}!", icon="⭐")

    data.setdefault("daily_completions", {}).setdefault(
        today, {k: 0 for k in data["kids"]}
    )

    done_today = sum(v for v in data["completions"][kid].values())
    data["daily_completions"][today][kid] = done_today

    ref.set(data)

# ─── UI ──────────────────────────────────────────────────────────────────
st.title("Ruby & Sofia Chore Manager")
st.subheader(f"Today: {today_display}")

# ─── Leaderboards ────────────────────────────────────────────────────────
st.markdown("### 🏆 Leaderboards")
today_rank, all_time_rank = get_leaderboard()

col1, col2 = st.columns(2)

with col1:
    st.subheader("Today's Race")
    for i, (kid, chores, _) in enumerate(today_rank, 1):
        medal = "🥇" if i == 1 else "🥈"
        st.markdown(f"{medal} **{kid}** – {chores} chores")

with col2:
    st.subheader("All-Time Champions")
    for i, (kid, pts, badges) in enumerate(all_time_rank, 1):
        medal = "🥇" if i == 1 else "🥈"
        st.markdown(f"{medal} **{kid}** – {pts} points • {badges} badges")

# ─── Parent Dashboard ────────────────────────────────────────────────────
st.markdown("---")
st.markdown("## 🔐 Parent Dashboard")

if st.checkbox("Parent Login"):
    password = st.text_input("Enter Parent Password", type="password")

    if password == ADMIN_PASSWORD:
        st.success("Parent Mode Active")

        # Reset buttons
        if st.button("Reset All Points"):
            for k in data["kids"]:
                data["points"][k] = 0
            ref.set(data)

        if st.button("Reset Today's Completions"):
            data["completions"] = {}
            data["daily_completions"][today] = {k: 0 for k in data["kids"]}
            ref.set(data)

        # Bonus points
        kid = st.selectbox("Select Kid", data["kids"])
        bonus = st.number_input("Bonus Points", 1, 100, 10)
        if st.button("Add Bonus"):
            data["points"][kid] += bonus
            ref.set(data)

        # ➕ Add Chore
        st.markdown("### ➕ Add New Chore")
        new_chore = st.text_input("Chore name")

        if st.button("Add Chore"):
            new_chore = new_chore.strip()
            if not new_chore:
                st.error("Chore cannot be empty")
            elif new_chore in data["chores"]:
                st.warning("Chore already exists")
            else:
                data["chores"].append(new_chore)
                ref.set(data)
                st.success(f"Added: {new_chore}")

    elif password:
        st.error("Incorrect password")

# ─── Chores ──────────────────────────────────────────────────────────────
st.markdown("### Today's Chores")

for kid in data["kids"]:
    st.subheader(kid)
    for chore in data["chores"]:
        key = f"{kid}_{chore}"
        st.checkbox(
            chore,
            value=data.get("completions", {}).get(kid, {}).get(chore, False),
            key=key,
            on_change=on_chore_change,
            args=(kid, chore, key)
        )

# ─── Progress ────────────────────────────────────────────────────────────
st.markdown("### Progress & Rewards")

for kid in data["kids"]:
    pts = data["points"][kid]
    st.markdown(f"**{kid}** · {get_level(pts)}")
    st.progress(min(pts / 400, 1.0), text=get_reward(pts))
    st.markdown("---")

st.caption("Flynnchilada • Firebase • Streamlit")