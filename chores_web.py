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
        "Feed Dog", "Dog Poo", "Feed Cat", "Clean Kitty Litter",
        "Take out rubbish", "Put away Dishes", "Clean Rooms"
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

# ─── Weekly + Daily Chore Assignment ─────────────────────────────────────
def auto_assign_chores(data):
    kids = data["kids"]
    data["assignments"] = {k: [] for k in kids}

    # Fixed chores per kid
    fixed_chores = {
        "Ruby": ["Feed Dog", "Dog Poo"],
        "Sofia": ["Feed Cat", "Clean Kitty Litter"]
    }

    # Assign fixed chores
    for kid in kids:
        data["assignments"][kid].extend(fixed_chores.get(kid, []))

    # Shared daily chore
    for kid in kids:
        data["assignments"][kid].append(SHARED_CHORE)

    # Weekly rotating chores
    weekly_chores = ["Take out rubbish", "Put away Dishes"]
    week_number = today.isocalendar()[1]

    for i, chore in enumerate(weekly_chores):
        kid_index = (week_number + i) % len(kids)
        data["assignments"][kids[kid_index]].append(chore)

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

# ─── Chore Toggle Logic (Add/Remove points) ──────────────────────────────
def on_chore_change(kid, chore, key):
    new_value = st.session_state.get(key, False)
    old_value = data.get("completions", {}).get(kid, {}).get(chore, False)

    data.setdefault("completions", {}).setdefault(kid, {})
    data["completions"][kid][chore] = new_value

    data.setdefault("points", {}).setdefault(kid, 0)
    data.setdefault("total_chores_completed", {}).setdefault(kid, 0)

    if new_value and not old_value:
        data["points"][kid] += 10
        data["total_chores_completed"][kid] += 1
    elif not new_value and old_value:
        data["points"][kid] = max(data["points"][kid] - 10, 0)
        data["total_chores_completed"][kid] = max(data["total_chores_completed"][kid] - 1, 0)

    assigned = data.get("assignments", {}).get(kid, [])
    done_today = all(
        data.get("completions", {}).get(kid, {}).get(c, False) for c in assigned
    )

    if done_today:
        last = data.get("last_completed_date", {}).get(kid, "")
        yesterday = (today - timedelta(days=1)).isoformat()

        data.setdefault("streaks", {}).setdefault(kid, 0)

        if last == yesterday:
            data["streaks"][kid] += 1
        elif last != today_key:
            data["streaks"][kid] = 1

        data.setdefault("last_completed_date", {})[kid] = today_key
        check_and_award_badges(data, kid)

    ref.set(data)

# ─── UI ──────────────────────────────────────────────────────────────────
st.title("Ruby & Sofia Chore Manager")
st.subheader(f"Today: {today_display}")

data = get_data()

# ─── Parent Dashboard / Admin Panel ──────────────────────────────────────
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
            badges_list = data.get("badges", {}).get(kid, [])
            badges_str = " ".join(badges_list)
            st.markdown(f"- **{kid}**: {points} pts, {streak}🔥 streak, {chores_done} chores done {badges_str}")

        st.markdown("---")
        st.markdown("### Manage Chores")
        new_chore = st.text_input("Add new chore:")
        if st.button("Add Chore"):
            if new_chore and new_chore not in data.get("chores", []):
                data.setdefault("chores", []).append(new_chore)
                auto_assign_chores(data)
                ref.set(data)
                st.success(f"Added chore: {new_chore}")

        remove_chore = st.selectbox("Remove chore:", options=data.get("chores", []))
        if st.button("Remove Chore"):
            if remove_chore in data.get("chores", []):
                data["chores"].remove(remove_chore)
                auto_assign_chores(data)
                for kid in data.get("completions", {}):
                    data["completions"][kid].pop(remove_chore, None)
                ref.set(data)
                st.success(f"Removed chore: {remove_chore}")

        st.markdown("---")
        st.markdown("### Manage Streaks & Points")
        selected_kid = st.selectbox("Select Kid:", options=data.get("kids", []))

        if st.button("Reset Streaks"):
            for kid in data.get("kids", []):
                data.setdefault("streaks", {}).setdefault(kid, 0)
                data["streaks"][kid] = 0
            ref.set(data)
            st.success("All streaks reset!")

        points_change = st.number_input("Points to Add / Remove:", value=0)
        if st.button("Update Points"):
            data.setdefault("points", {}).setdefault(selected_kid, 0)
            data["points"][selected_kid] += points_change
            if data["points"][selected_kid] < 0:
                data["points"][selected_kid] = 0
            ref.set(data)
            st.success(f"{selected_kid} now has {data['points'][selected_kid]} points")

        st.markdown("---")
        st.markdown("### ⚠️ Reset Everything")
        if st.button("Reset Everything"):
            for kid in data.get("kids", []):
                data.setdefault("points", {}).setdefault(kid, 0)
                data["points"][kid] = 0
                data.setdefault("streaks", {}).setdefault(kid, 0)
                data["streaks"][kid] = 0
                data.setdefault("total_chores_completed", {}).setdefault(kid, 0)
                data["total_chores_completed"][kid] = 0
                data.setdefault("badges", {}).setdefault(kid, [])
                data["badges"][kid] = []
                if "completions" in data and kid in data["completions"]:
                    data["completions"][kid] = {}
            ref.set(data)
            st.success("All data reset! Points, streaks, badges, and completions cleared.")

    elif admin_input:
        st.error("Incorrect password")

# ─── Leaderboard ─────────────────────────────────────────────────────────
st.markdown("### 🏆 Leaderboard")
leaderboard = sorted(data.get("kids", []), key=lambda k: data.get("points", {}).get(k, 0), reverse=True)

for rank, kid in enumerate(leaderboard, start=1):
    badges = " ".join(data.get("badges", {}).get(kid, []))
    points = data.get("points", {}).get(kid, 0)
    streak = data.get("streaks", {}).get(kid, 0)

    if rank == 1:
        st.markdown(f"**{rank}. {kid} 🥇** – ⭐ {points} pts | 🔥 {streak} streak {badges}", unsafe_allow_html=True)
    else:
        st.markdown(f"**{rank}. {kid}** – ⭐ {points} pts | 🔥 {streak} streak {badges}")

# ─── Chores ──────────────────────────────────────────────────────────────
st.markdown("### Today's Chores")
weekly_chores = ["Take out rubbish", "Put away Dishes"]

for kid in data.get("kids", []):
    st.subheader(kid)
    for chore in data.get("assignments", {}).get(kid, []):
        key = f"{kid}_{chore}"

        # Highlight weekly rotating chore
        label = chore
        if chore in weekly_chores:
            label = f"🔄 **{chore} (this week's)**"

        st.checkbox(
            label,
            value=data.get("completions", {}).get(kid, {}).get(chore, False),
            key=key,
            on_change=on_chore_change,
            args=(kid, chore, key),
            help="Weekly rotating chore" if chore in weekly_chores else None,
            unsafe_allow_html=True
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