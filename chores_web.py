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
    data.setdefault("badges", {"Ruby": [], "Sofia": []})  # New: earned badges
    data.setdefault("total_chores_completed", {"Ruby": 0, "Sofia": 0})  # For badge tracking
    data.setdefault("family_all_done_count", 0)  # Family-wide perfect days

    # Default rewards (editable)
    data.setdefault("rewards", [
        {"points": 50,  "text": "Ice cream treat 🍦"},
        {"points": 100, "text": "Extra screen time 30 min 🎮"},
        {"points": 200, "text": "Movie night pick 🍿"},
        {"points": 300, "text": "Special family outing 🌟"}
    ])

    ref.set(data)
    return data

data = get_data()

# ─── Dynamic reward & level ──────────────────────────────────────────────────────
def get_level(points):
    if points >= 300: return "Level 4 - Superstar 🌟"
    if points >= 200: return "Level 3 - Champion 🏆"
    if points >= 100: return "Level 2 - Rising Hero 🚀"
    return "Level 1 - Starter 🌱"

def get_reward(points):
    rewards = sorted(data.get("rewards", []), key=lambda x: x["points"], reverse=True)
    for r in rewards:
        if points >= r["points"]:
            return r["text"]
    return "Keep going! Next reward soon"

# ─── Badge definitions & check ───────────────────────────────────────────────────
BADGES = {
    "Streak Star": {"desc": "7-day streak", "icon": "⭐", "condition": lambda s: s >= 7},
    "Chore Champion": {"desc": "50 chores completed", "icon": "🏅", "condition": lambda c: c >= 50},
    "Family Hero": {"desc": "10 perfect family days", "icon": "🦸", "condition": lambda f: f >= 10},
    "Perfect Week": {"desc": "All chores done 7 days in a row", "icon": "🔥", "condition": lambda s: s >= 7 and data["family_all_done_count"] >= 1}
}

def check_and_award_badges():
    updated = False
    for kid in data["kids"]:
        badges = data["badges"].get(kid, [])
        streak = data["streaks"].get(kid, 0)
        completed = data["total_chores_completed"].get(kid, 0)

        for badge_name, info in BADGES.items():
            if badge_name not in badges and info["condition"](streak if "Streak" in badge_name else completed):
                badges.append(badge_name)
                updated = True
                st.toast(f"{kid} earned badge: {info['icon']} {badge_name}!", icon="🎖️")

        data["badges"][kid] = badges

    if updated:
        ref.set(data)

check_and_award_badges()

# Early defs
assignments = data.get("last_assignments", {})
completions = data.get("completions", {})

# ─── Update streaks & points ─────────────────────────────────────────────────────
def update_streaks_and_points():
    yesterday_str = (date.today() - timedelta(days=1)).isoformat()

    streaks = data.get("streaks", {"Ruby": 0, "Sofia": 0})
    last_completed = data.get("last_completed_days", {"Ruby": None, "Sofia": None})
    points = data.get("points", {"Ruby": 0, "Sofia": 0})

    total_chores = sum(len(t) for t in assignments.values())
    done_chores = sum(sum(1 for v in c.values() if v) for c in completions.values())

    all_done = total_chores > 0 and done_chores == total_chores

    if all_done:
        data["family_all_done_count"] = data.get("family_all_done_count", 0) + 1

    for kid in data["kids"]:
        if all_done:
            points[kid] += 50

        last_day = last_completed.get(kid)
        streak = streaks.get(kid, 0)

        if all_done:
            streak = streak + 1 if last_day == yesterday_str else 1
            last_completed[kid] = today
        else:
            streak = 0

        streaks[kid] = streak

    data["points"] = points
    data["streaks"] = streaks
    data["last_completed_days"] = last_completed
    ref.set(data)

    # Check badges after update
    check_and_award_badges()

update_streaks_and_points()

# ─── Admin check ─────────────────────────────────────────────────────────────────
is_admin = False
with st.sidebar:
    st.markdown("**Parent Admin**")
    pw = st.text_input("Password", type="password", key="pw")
    if pw == ADMIN_PASSWORD:
        is_admin = True
        st.success("Admin OK")
    elif pw:
        st.error("Wrong password")

# ─── Main UI ─────────────────────────────────────────────────────────────────────
st.title("Ruby & Sofia Chore Manager")
st.subheader(f"Today: {today_display}")

if is_admin:
    st.header("Admin Dashboard")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Current Status")
        for kid in data["kids"]:
            p = data["points"].get(kid, 0)
            s = data["streaks"].get(kid, 0)
            lvl = get_level(p)
            badges = data["badges"].get(kid, [])
            st.markdown(f"**{kid}** · {lvl}")
            st.markdown(f"Points: **{p}** · Streak: **{s}** 🔥")
            st.caption(f"Reward: {get_reward(p)}")
            if badges:
                st.write("Badges: " + " ".join([f"{BADGES[b]['icon']}" for b in badges]))
            st.markdown("---")

    with col2:
        # ... (manual adjustments, reward tiers, chores management remain the same)
        # (copy from previous version if needed - omitted here for brevity)

else:
    # Kid view - chores loop remains the same as last fix
    # ... (keep your existing Generate button and checkbox loop)

# ─── Progress & Rewards ──────────────────────────────────────────────────────────
st.markdown("### Progress & Rewards")
for kid in data["kids"]:
    p = data["points"].get(kid, 0)
    s = data["streaks"].get(kid, 0)
    lvl = get_level(p)
    badges = data["badges"].get(kid, [])

    st.markdown(f"**{kid}** · {lvl}")
    st.markdown(f"🔥 Streak: **{s}** day{'s' if s != 1 else ''}")
    st.markdown(f"⭐ Points: **{p}**")
    st.progress(min(p / 300, 1.0), text=f"Next: {get_reward(p)}")

    if badges:
        st.markdown("**Badges earned**")
        cols = st.columns(len(badges))
        for i, b in enumerate(badges):
            cols[i].markdown(f"<div title='{BADGES[b]['desc']}'>{BADGES[b]['icon']} {b}</div>", unsafe_allow_html=True)

    st.markdown("---")

# ─── Celebration ─────────────────────────────────────────────────────────────────
if assignments:
    total = sum(len(v) for v in assignments.values())
    done = sum(sum(1 for v in c.values() if v) for c in completions.values())
    if total > 0 and done == total:
        st.balloons()
        st.markdown("### 🎉 ALL DONE TODAY! 🎉")
        st.markdown("Great job Ruby & Sofia! 🌟")

st.caption("Flynnchilada • Firebase • Add to home screen")