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
        service_account_str = st.secrets["firebase"]["service_account_json"]
        service_account_info = json.loads(service_account_str)

        cred = credentials.Certificate(service_account_info)

        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://chores-1a1ac-default-rtdb.asia-southeast1.firebasedatabase.app/'
        }, name=APP_NAME)

    except Exception as e:
        st.error("Firebase connection failed")
        st.error(str(e))
        st.error("Verify the 'firebase' → 'service_account_json' secret in app Settings.")
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
    
    # Ensure all fields
    for field in ["points", "streaks", "last_completed_days"]:
        if field not in data:
            data[field] = {"Ruby": 0 if field == "points" else 0 if field == "streaks" else None}
    
    return data

data = get_data()

# ─── Admin Password (CHANGE THIS!) ───────────────────────────────────────────────
ADMIN_PASSWORD = "Harlindon2026"  # ← CHANGE THIS TO SOMETHING ONLY YOU KNOW

# ─── Check if user is admin ──────────────────────────────────────────────────────
is_admin = False
with st.sidebar:
    st.markdown("**Parent Admin**")
    password_input = st.text_input("Enter admin password", type="password", key="admin_pw")
    if password_input == ADMIN_PASSWORD:
        is_admin = True
        st.success("Admin access granted")
    elif password_input:
        st.error("Wrong password")

# ─── Update Streaks & Points ─────────────────────────────────────────────────────
def update_streaks_and_points():
    today_str = date.today().isoformat()
    yesterday_str = (date.today() - timedelta(days=1)).isoformat()

    assignments = data.get("last_assignments", {})
    completions = data.get("completions", {})
    streaks = data.get("streaks", {"Ruby": 0, "Sofia": 0})
    last_completed = data.get("last_completed_days", {"Ruby": None, "Sofia": None})
    points = data.get("points", {"Ruby": 0, "Sofia": 0})

    if not assignments:
        return

    total_chores = sum(len(tasks) for tasks in assignments.values())
    done_chores = sum(
        sum(1 for v in kid_compl.values() if v)
        for kid_compl in completions.values()
    )

    all_done_today = total_chores > 0 and done_chores == total_chores

    for kid in data["kids"]:
        kid_tasks = len(assignments.get(kid, []))
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
    if points >= 300:
        return "Special family outing 🌟"
    elif points >= 200:
        return "Movie night pick 🍿"
    elif points >= 100:
        return "Extra screen time 30 min 🎮"
    elif points >= 50:
        return "Ice cream treat 🍦"
    else:
        return "Keep going! Next reward at 50 points"

# ─── App UI ──────────────────────────────────────────────────────────────────────
st.title("Ruby & Sofia Chore Manager")

today = date.today().strftime("%A, %d %B %Y")
st.subheader(f"Today: {today}")

# ─── Kid View / Admin View ───────────────────────────────────────────────────────
if is_admin:
    st.markdown("### Admin Dashboard (Parent Only)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Current Status")
        for kid in data["kids"]:
            points = data["points"].get(kid, 0)
            streak = data["streaks"].get(kid, 0)
            st.markdown(f"**{kid}**")
            st.markdown(f"Points: **{points}**")
            st.markdown(f"Streak: **{streak}** days 🔥")
            st.markdown(f"Reward: {get_reward(points)}")
            st.markdown("---")
    
    with col2:
        st.subheader("Manual Adjustments")
        selected_kid = st.selectbox("Select kid", data["kids"])
        adjustment = st.number_input("Add/subtract points", value=0, step=10)
        if st.button("Apply Points Change"):
            data["points"][selected_kid] += adjustment
            ref.set(data)
            st.success(f"{adjustment} points applied to {selected_kid}")
            st.rerun()
        
        if st.button("Reset All Streaks & Points"):
            if st.checkbox("Are you sure? This cannot be undone"):
                data["streaks"] = {"Ruby": 0, "Sofia": 0}
                data["points"] = {"Ruby": 0, "Sofia": 0}
                data["last_completed_days"] = {"Ruby": None, "Sofia": None}
                ref.set(data)
                st.success("Streaks and points reset")
                st.rerun()

    # Admin chore management
    st.subheader("Manage Chores List")
    current_chores = data["chores"]
    new_chore = st.text_input("Add new chore")
    if st.button("Add Chore") and new_chore:
        if new_chore not in current_chores:
            current_chores.append(new_chore)
            data["chores"] = current_chores
            ref.set(data)
            st.success(f"Added: {new_chore}")
            st.rerun()
    
    st.write("Current chores:")
    for chore in current_chores:
        col_chore, col_del = st.columns([4, 1])
        col_chore.write(chore)
        if col_del.button("Remove", key=f"del_{chore}"):
            current_chores.remove(chore)
            data["chores"] = current_chores
            ref.set(data)
            st.rerun()

else:
    # Normal kid view
    if st.button("Generate New Assignments", type="primary"):
        chores_copy = data["chores"][:]
        random.shuffle(chores_copy)

        assignments = {kid: [] for kid in data["kids"]}
        for i, chore in enumerate(chores_copy):
            kid = data["kids"][i % len(data["kids"])]
            assignments[kid].append(chore)

        completions = {
            kid: {chore: False for chore in tasks}
            for kid, tasks in assignments.items()
        }

        data["last_date"] = today
        data["last_assignments"] = assignments
        data["completions"] = completions
        data["last_completed_days"] = {kid: None for kid in data["kids"]}

        ref.set(data)
        st.success("New assignments created and synced!")
        st.rerun()

    st.markdown("### Today's Chores")

    assignments = data.get("last_assignments", {})
    completions = data.get("completions", {})

    updated = False

    for kid in sorted(assignments.keys()):
        st.markdown(f"**★ {kid}**")
        tasks = assignments.get(kid, [])

        if not tasks:
            st.info("No chores today – nice break!")
            continue

        for chore in sorted(tasks):
            key = f"{kid}_{chore.replace(' ', '_').replace("'", '')}"
            current_done = completions.get(kid, {}).get(chore, False)

            done = st.checkbox(
                chore,
                value=current_done,
                key=key
            )

            if done != current_done:
                data.setdefault("completions", {}).setdefault(kid, {})[chore] = done
                updated = True

    if updated:
        ref.set(data)
        update_streaks_and_points()
        st.success("Changes saved and synced!")
        st.rerun()

    # Streaks & Points for kids
    st.markdown("### Your Progress")
    for kid in data["kids"]:
        streak = data["streaks"].get(kid, 0)
        points = data["points"].get(kid, 0)
        reward = get_reward(points)
        st.markdown(f"**{kid}**")
        st.markdown(f"🔥 Streak: **{streak}** days")
        st.markdown(f"⭐ Points: **{points}**")
        st.progress(min(points / 300, 1.0), text=f"Next: {reward}")

# ─── Celebration ─────────────────────────────────────────────────────────────────
if assignments:
    total_chores = sum(len(tasks) for tasks in assignments.values())
    done_chores = sum(
        sum(1 for v in kid_compl.values() if v)
        for kid_compl in completions.values()
    )

    if total_chores > 0 and done_chores == total_chores:
        st.balloons()
        st.markdown(
            """
            <div style="text-align:center; font-size:2.8em; color:#2ecc71; margin:40px 0;">
            🎉 ALL DONE TODAY! 🎉
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown(
            "<p style='text-align:center; font-size:1.4em; color:#27ae60;'>"
            "You're legends Ruby & Sofia! 🌟 Keep the streak & points growing!"
            "</p>",
            unsafe_allow_html=True
        )

if st.button("Refresh / Sync Now"):
    st.rerun()

if not assignments:
    st.info("No assignments yet. Generate new ones to start!")

st.markdown("---")
st.caption("App by Flynnchilada • Synced via Firebase • Add to iPhone home screen")