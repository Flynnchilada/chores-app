# ─── IMPORTS ─────────────────────────────────────────────────────────────
import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import json
from datetime import date, timedelta

# ─── CONFIG ─────────────────────────────────────────────────────────────
ADMIN_PASSWORD = "parent123"
SHARED_CHORE = "Clean Rooms"

today = date.today()
today_key = today.isoformat()
today_display = today.strftime('%A, %d %B %Y')

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
        "Clean Rooms",
        "Feed dog",
        "Feed cat",
        "Clean kitty litter",
        "Put away dishes",
        "Put away clothes",
        "Take out rubbish bins",
        "Wipe kitchen bench"
    ])
    data.setdefault("assignments", {})
    data.setdefault("completions", {})
    data.setdefault("points", {k: 0 for k in data["kids"]})

    data.setdefault("streaks", {k: 0 for k in data["kids"]})
    data.setdefault("last_completed_date", {k: "" for k in data["kids"]})
    data.setdefault("total_chores_completed", {k: 0 for k in data["kids"]})
    data.setdefault("badges", {k: [] for k in data["kids"]})

    auto_assign_chores(data)

    ref.set(data)
    return data

# ─── Daily Rotation Assignment ───────────────────────────────────────────
def auto_assign_chores(data):
    kids = data["kids"]
    chores = data["chores"]

    epoch = date(2024, 1, 1)
    rotation_offset = (today - epoch).days % len(kids)

    normal_chores = [c for c in chores if c != SHARED_CHORE]

    data["assignments"] = {k: [] for k in kids}

    for i, chore in enumerate(normal_chores):
        kid_index = (i + rotation_offset) % len(kids)
        data["assignments"][kids[kid_index]].append(chore)

    for kid in kids:
        data["assignments"][kid].append(SHARED_CHORE)

# ─── Badge Logic ─────────────────────────────────────────────────────────
BADGE_RULES = [
    ("First Steps 🥉", lambda d, k: d.get("total_chores_completed", {}).get(k, 0) >= 1),
    ("Helping Hand 🥈", lambda d, k: d.get("total_chores_completed", {}).get(k, 0) >= 10),
    ("Chore Champion 🥇", lambda d, k: d.get("total_chores_completed", {}).get(k, 0) >= 25),
    ("Streak Star 🔥", lambda d, k: d.get("streaks", {}).get(k, 0) >= 5),
    ("Super Streak 🌟", lambda d, k: d.get("streaks", {}).get(k, 0) >= 10),
]

def check_and_award_badges(data, kid):
    for badge, rule in BADGE_RULES:
        if rule(data, kid) and badge not in data.get("badges", {}).get(kid, []):
            data.setdefault("badges", {}).setdefault(kid, []).append(badge)
            st.toast(f"{kid} earned badge: {badge}", icon="🏅")

# ─── Chore Toggle Logic ──────────────────────────────────────────────────
def on_chore_change(kid, chore, key):
    new_value = st.session_state.get(key, False)
    old_value = data.get("completions", {}).get(kid, {}).get(chore, False)

    data.setdefault("completions", {}).setdefault(kid, {})
    data["completions"][kid][chore] = new_value

    if new_value and not old_value:
        data.setdefault("points", {}).setdefault(kid, 0)
        data["points"][kid] += 10
        data.setdefault("total_chores_completed", {}).setdefault(kid, 0)
        data["total_chores_completed"][kid] += 1

    # Check if all assigned chores done today
    assigned = data.get("assignments", {}).get(kid, [])
    done_today = all(
        data.get("completions", {}).get(kid, {}).get(c, False) for c in assigned
    )

    if done_today:
        last = data.get("last_completed_date", {}).get(kid, "")
        yesterday = (today - timedelta(days=1)).isoformat()

        if last == yesterday:
            data.setdefault("streaks", {}).setdefault(kid, 0)
            data["streaks"][kid] += 1
        elif last != today_key:
            data.setdefault("streaks", {}).setdefault(kid, 0)
            data["streaks"][kid] = 1

        data.setdefault("last_completed_date", {})[kid] = today_key
        check_and_award_badges(data, kid)

    ref.set(data)

# ─── UI ──────────────────────────────────────────────────────────────────
st.title("Ruby & Sofia Chore Manager")
st.subheader(f"Today: {today_display}")

data = get_data()

# ─── Parent Dashboard ────────────────────────────────────────────────────
with st.expander("Parent Dashboard 🔒", expanded=True):
    admin_input = st.text_input("Enter admin password:", type="password")
    if admin_input == ADMIN_PASSWORD:
        st.markdown("### Family Overview")
        total_points = sum(data.get('points', {}).values())
        total_chores = sum(data.get('total_chores_completed', {}).values())
        avg_streak = (sum(data.get('streaks', {}).values()) / len(data.get('kids', []))) if data.get('kids') else 0

        st.markdown(f"**Total Points:** {total_points}")
        st.markdown(f"**Total Chores Completed:** {total_chores}")
        st.markdown(f"**Average Streak:** {avg_streak:.1f}")

        st.markdown("#### Individual Stats")
        for kid in data.get("kids", []):
            points = data.get("points", {}).get(kid, 0)
            streak = data.get("streaks", {}).get(kid, 0)
            chores_done = data.get("total_chores_completed", {}).get(kid, 0)
            st.markdown(f"- **{kid}**: {points} pts, {streak}🔥 streak, {chores_done} chores done")
    elif admin_input:
        st.error("Incorrect password")

# ─── Leaderboard ─────────────────────────────────────────────────────────
st.markdown("### 🏆 Leaderboard")
leaderboard = sorted(data.get("kids", []), key=lambda k: data.get("points", {}).get(k, 0), reverse=True)
for rank, kid in enumerate(leaderboard, start=1):
    badges = " ".join(data.get("badges", {}).get(kid, []))
    points = data.get("points", {}).get(kid, 0)
    streak = data.get("streaks", {}).get(kid, 0)
    st.markdown(f"**{rank}. {kid}** – ⭐ {points} pts | 🔥 {streak} streak {badges}")

# ─── Chores ──────────────────────────────────────────────────────────────
st.markdown("### Today's Chores")
for kid in data.get("kids", []):
    st.subheader(kid)
    for chore in data.get("assignments", {}).get(kid, []):
        key = f"{kid}_{chore}"
        st.checkbox(
            chore,
            value=data.get("completions", {}).get(kid, {}).get(chore, False),
            key=key,
            on_change=on_chore_change,
            args=(kid, chore, key)
        )

# ─── Progress & Rewards ──────────────────────────────────────────────────
st.markdown("### Progress")
for kid in data.get("kids", []):
    st.markdown(f"**{kid}**")
    points = data.get("points", {}).get(kid, 0)
    streak = data.get("streaks", {}).get(kid, 0)
    st.markdown(f"⭐ Points: {points}")
    st.markdown(f"🔥 Streak: {streak}")
    st.progress(min(points / 300, 1.0))

    badges_list = data.get("badges", {}).get(kid, [])
    if badges_list:
        st.markdown("🏅 Badges:")
        for b in badges_list:
            st.markdown(f"- {b}")

    st.markdown("---")

st.caption("Flynnchilada • Firebase • Streamlit")