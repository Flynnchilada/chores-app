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
    ("First Steps 🥉", lambda d, k: d["total_chores_completed"][k] >= 1),
    ("Helping Hand 🥈", lambda d, k: d["total_chores_completed"][k] >= 10),
    ("Chore Champion 🥇", lambda d, k: d["total_chores_completed"][k] >= 25),
    ("Streak Star 🔥", lambda d, k: d["streaks"][k] >= 5),
    ("Super Streak 🌟", lambda d, k: d["streaks"][k] >= 10),
]

def check_and_award_badges(data, kid):
    for badge, rule in BADGE_RULES:
        if rule(data, kid) and badge not in data["badges"][kid]:
            data["badges"][kid].append(badge)
            st.toast(f"{kid} earned badge: {badge}", icon="🏅")

# ─── Chore Toggle Logic ──────────────────────────────────────────────────
def on_chore_change(kid, chore, key):
    new_value = st.session_state.get(key, False)
    old_value = data.get("completions", {}).get(kid, {}).get(chore, False)

    data.setdefault("completions", {}).setdefault(kid, {})
    data["completions"][kid][chore] = new_value

    if new_value and not old_value:
        data["points"][kid] += 10
        data["total_chores_completed"][kid] += 1

    # Check if all assigned chores done today
    assigned = data["assignments"].get(kid, [])
    done_today = all(
        data["completions"].get(kid, {}).get(c, False) for c in assigned
    )

    if done_today:
        last = data["last_completed_date"].get(kid)
        yesterday = (today - timedelta(days=1)).isoformat()

        if last == yesterday:
            data["streaks"][kid] += 1
        elif last != today_key:
            data["streaks"][kid] = 1

        data["last_completed_date"][kid] = today_key
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
        total_points = sum(data['points'].values())
        total_chores = sum(data['total_chores_completed'].values())
        avg_streak = sum(data['streaks'].values()) / len(data['kids'])

        st.markdown(f"**Total Points:** {total_points}")
        st.markdown(f"**Total Chores Completed:** {total_chores}")
        st.markdown(f"**Average Streak:** {avg_streak:.1f}")

        st.markdown("#### Individual Stats")
        for kid in data["kids"]:
            st.markdown(f"- **{kid}**: {data['points'][kid]} pts, "
                        f"{data['streaks'][kid]}🔥 streak, "
                        f"{data['total_chores_completed'][kid]} chores done")
    elif admin_input:
        st.error("Incorrect password")

# ─── Chores ──────────────────────────────────────────────────────────────
st.markdown("### Today's Chores")

for kid in data["kids"]:
    st.subheader(kid)
    for chore in data["assignments"][kid]:
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

for kid in data["kids"]:
    st.markdown(f"**{kid}**")
    st.markdown(f"⭐ Points: {data['points'][kid]}")
    st.markdown(f"🔥 Streak: {data['streaks'][kid]}")
    st.progress(min(data["points"][kid] / 300, 1.0))

    if data["badges"][kid]:
        st.markdown("🏅 Badges:")
        for b in data["badges"][kid]:
            st.markdown(f"- {b}")

    st.markdown("---")

st.caption("Flynnchilada • Firebase • Streamlit")