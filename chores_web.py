import streamlit as st
import firebase_admin
from firebase_admin import credentials, db, _apps
import random
import json
from datetime import date, timedelta

# ─── Firebase Setup ──────────────────────────────────────────────────────────────
APP_NAME = 'chores-family-app'

if APP_NAME not in _apps:
    try:
        # Load from Streamlit secrets
        service_account_str = st.secrets["firebase"]["service_account_json"]
        service_account_info = json.loads(service_account_str)

        # Define cred HERE (this line was missing or misplaced)
        cred = credentials.Certificate(service_account_info)

        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://chores-1a1ac-default-rtdb.asia-southeast1.firebasedatabase.app/'
        }, name=APP_NAME)

    except Exception as e:
        st.error(f"Firebase init failed: {str(e)}")
        st.error("Check secrets: [firebase] service_account_json")
        st.stop()

# Database reference
DB_PATH = "/chores/ruby_sofia"
ref = db.reference(DB_PATH)

# ─── Load or Initialize Data ─────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def get_data():
    data = ref.get()
    if data is None:
        default_data = {
            "kids": ["Ruby", "Sofia"],
            "chores": [
                "Feed dog", "Do dog poo",
                "Feed cat", "Clean kitty litter",
                "Put away dishes", "Put away clean clothes",
                "Take out rubbish bins", "Wipe kitchen bench"
            ],
            "last_date": None,
            "last_assignments": None,
            "completions": {},
            "streaks": {"Ruby": 0, "Sofia": 0},
            "last_completed_days": {"Ruby": None, "Sofia": None},
            "points": {"Ruby": 0, "Sofia": 0},
        }
        ref.set(default_data)
        return default_data

    # Ensure required fields
    data.setdefault("points", {"Ruby": 0, "Sofia": 0})
    data.setdefault("streaks", {"Ruby": 0, "Sofia": 0})
    data.setdefault("last_completed_days", {"Ruby": None, "Sofia": None})
    return data

data = get_data()

# Define these early so they're always available
assignments = data.get("last_assignments", {})
completions = data.get("completions", {})

# ─── Update Streaks & Points ─────────────────────────────────────────────────────
def update_streaks_and_points():
    today_str = date.today().isoformat()
    yesterday_str = (date.today() - timedelta(days=1)).isoformat()

    streaks = data.get("streaks", {"Ruby": 0, "Sofia": 0})
    last_completed = data.get("last_completed_days", {"Ruby": None, "Sofia": None})
    points = data.get("points", {"Ruby": 0, "Sofia": 0})

    if not assignments:
        return

    total_chores = sum(len(tasks) for tasks in assignments.values())
    done_chores = sum(sum(1 for v in kid_compl.values() if v) for kid_compl in completions.values())

    all_done_today = total_chores > 0 and done_chores == total_chores

    for kid in data["kids"]:
        kid_done = sum(1 for v in completions.get(kid, {}).values() if v)
        points[kid] += kid_done * 10
        if all_done_today:
            points[kid] += 50

        last_day = last_completed.get(kid)
        current_streak = streaks.get(kid, 0)

        if all_done_today:
            if last_day == yesterday_str:
                current_streak += 1
            else:
                current_streak = 1
            last_completed[kid] = today_str
        else:
            current_streak = 0

        streaks[kid] = current_streak

    data["points"] = points
    data["streaks"] = streaks
    data["last_completed_days"] = last_completed
    ref.set(data)

update_streaks_and_points()

# ─── Reward Tiers ────────────────────────────────────────────────────────────────
def get_reward(points):
    if points >= 300: return "Special family outing 🌟"
    if points >= 200: return "Movie night pick 🍿"
    if points >= 100: return "Extra screen time 30 min 🎮"
    if points >= 50:  return "Ice cream treat 🍦"
    return "Keep going! Next reward at 50 points"

# ─── Admin Password (CHANGE THIS!) ───────────────────────────────────────────────
ADMIN_PASSWORD = "parent123"  # ← CHANGE TO SOMETHING SECURE ONLY YOU KNOW

# ─── Admin Check ─────────────────────────────────────────────────────────────────
is_admin = False
with st.sidebar:
    st.markdown("**Parent Admin**")
    pw = st.text_input("Admin password", type="password", key="admin_pw")
    if pw == ADMIN_PASSWORD:
        is_admin = True
        st.success("Admin access granted")
    elif pw:
        st.error("Wrong password")

# ─── Main UI ─────────────────────────────────────────────────────────────────────
st.title("Ruby & Sofia Chore Manager")
st.subheader(f"Today: {date.today().strftime('%A, %d %B %Y')}")

if is_admin:
    st.markdown("### Admin Dashboard (Parent Only)")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Current Status")
        for kid in data["kids"]:
            pts = data["points"].get(kid, 0)
            strk = data["streaks"].get(kid, 0)
            st.markdown(f"**{kid}**")
            st.markdown(f"Points: **{pts}**")
            st.markdown(f"Streak: **{strk}** days 🔥")
            st.markdown(f"Reward: {get_reward(pts)}")
            st.markdown("---")

    with col2:
        st.subheader("Manual Adjustments")
        kid = st.selectbox("Select kid", data["kids"], key="adj_kid")
        adj = st.number_input("Points ±", value=0, step=10, key="adj_val")

        if st.button("Apply Points Change", key="btn_apply"):
            if adj != 0:
                data["points"][kid] = data["points"].get(kid, 0) + adj
                ref.set(data)
                st.success(f"{adj:+} points → {kid} now has {data['points'][kid]}")
                st.rerun()

        if st.button("Reset All Streaks & Points", key="btn_reset"):
            if st.checkbox("Confirm reset", key="chk_reset"):
                data["streaks"] = {"Ruby": 0, "Sofia": 0}
                data["points"] = {"Ruby": 0, "Sofia": 0}
                data["last_completed_days"] = {"Ruby": None, "Sofia": None}
                ref.set(data)
                st.success("Reset complete")
                st.rerun()

    st.subheader("Manage Chores")
    chores = data.get("chores", [])

    new_chore = st.text_input("New chore", key="new_chore")
    if st.button("Add Chore", key="btn_add_chore") and new_chore.strip():
        c = new_chore.strip()
        if c not in chores:
            chores.append(c)
            data["chores"] = chores
            ref.set(data)
            st.success(f"Added: {c}")
            st.rerun()

    st.write("Current chores:")
    for c in chores:
        cols = st.columns([5, 1])
        cols[0].write(c)
        if cols[1].button("Remove", key=f"rm_{c}"):
            chores.remove(c)
            data["chores"] = chores
            ref.set(data)
            st.rerun()

else:
    # Kid view
    if st.button("Generate New Assignments", type="primary"):
        chores_copy = data["chores"][:]
        random.shuffle(chores_copy)

        ass = {k: [] for k in data["kids"]}
        for i, chore in enumerate(chores_copy):
            ass[data["kids"][i % len(data["kids"])]].append(chore)

        comp = {k: {ch: False for ch in tsk} for k, tsk in ass.items()}

        data.update({
            "last_date": today,
            "last_assignments": ass,
            "completions": comp,
            "last_completed_days": {k: None for k in data["kids"]}
        })
        ref.set(data)
        st.success("New assignments created!")
        st.rerun()

    st.markdown("### Today's Chores")

    updated = False

    for kid in sorted(assignments.keys()):
        st.markdown(f"**★ {kid}**")
        tasks = assignments.get(kid, [])

        if not tasks:
            st.info("No chores today – enjoy!")
            continue

        for chore in sorted(tasks):
            key = f"{kid}_{chore.replace(' ', '_').replace("'", '')}"
            cur = completions.get(kid, {}).get(chore, False)

            done = st.checkbox(chore, value=cur, key=key)

            if done != cur:
                data.setdefault("completions", {}).setdefault(kid, {})[chore] = done
                updated = True

    if updated:
        ref.set(data)
        update_streaks_and_points()
        st.success("Saved & synced!")
        st.rerun()

# ─── Progress Display ────────────────────────────────────────────────────────────
st.markdown("### Progress & Rewards")

for kid in data["kids"]:
    strk = data["streaks"].get(kid, 0)
    pts = data["points"].get(kid, 0)
    rew = get_reward(pts)
    st.markdown(f"**{kid}**")
    st.markdown(f"🔥 Streak: **{strk}** day{'s' if strk != 1 else ''}")
    st.markdown(f"⭐ Points: **{pts}**")
    st.progress(min(pts / 300, 1.0), text=f"Next: {rew}")
    st.caption(f"Reward: {rew}")
    st.markdown("---")

# ─── Celebration ─────────────────────────────────────────────────────────────────
if assignments:
    total = sum(len(t) for t in assignments.values())
    done = sum(sum(1 for v in c.values() if v) for c in completions.values())

    if total > 0 and done == total:
        st.balloons()
        st.markdown("<h2 style='text-align:center; color:#2ecc71'>🎉 ALL DONE TODAY! 🎉</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; font-size:1.3em; color:#27ae60'>Great job Ruby & Sofia! 🌟 Keep going!</p>", unsafe_allow_html=True)

# Refresh
if st.button("Refresh / Sync Now"):
    st.rerun()

if not assignments:
    st.info("No assignments yet — generate some!")

st.markdown("---")
st.caption("App by Flynnchilada • Firebase sync • Add to iPhone home screen")