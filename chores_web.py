import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import random
import json
from datetime import date, timedelta

# ─── Firebase Setup ──────────────────────────────────────────────────────────────
try:
    service_account_str = st.secrets["firebase"]["service_account_json"]
    service_account_info = json.loads(service_account_str)

    # This line MUST come before initialize_app
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
    data.setdefault("chores", ["Feed dog", "Do dog poo", "Feed cat", "Clean kitty litter",
                               "Put away dishes", "Put away clean clothes",
                               "Take out rubbish bins", "Wipe kitchen bench"])
    data.setdefault("last_date", None)
    data.setdefault("last_assignments", {})
    data.setdefault("completions", {})
    data.setdefault("streaks", {"Ruby": 0, "Sofia": 0})
    data.setdefault("last_completed_days", {"Ruby": None, "Sofia": None})
    data.setdefault("points", {"Ruby": 0, "Sofia": 0})
    ref.set(data)  # ensure structure saved
    return data

data = get_data()

# Define early to avoid NameError
assignments = data.get("last_assignments", {})
completions = data.get("completions", {})

# ─── Update streaks & points ─────────────────────────────────────────────────────
def update_streaks_and_points():
    today_str = date.today().isoformat()
    yesterday_str = (date.today() - timedelta(days=1)).isoformat()

    streaks = data.get("streaks", {"Ruby": 0, "Sofia": 0})
    last_completed = data.get("last_completed_days", {"Ruby": None, "Sofia": None})
    points = data.get("points", {"Ruby": 0, "Sofia": 0})

    total_chores = sum(len(t) for t in assignments.values())
    done_chores = sum(sum(1 for v in c.values() if v) for c in completions.values())

    all_done = total_chores > 0 and done_chores == total_chores

    for kid in data["kids"]:
        kid_done = sum(1 for v in completions.get(kid, {}).values() if v)
        points[kid] += kid_done * 10
        if all_done:
            points[kid] += 50

        last_day = last_completed.get(kid)
        streak = streaks.get(kid, 0)

        if all_done:
            streak = streak + 1 if last_day == yesterday_str else 1
            last_completed[kid] = today_str
        else:
            streak = 0

        streaks[kid] = streak

    data["points"] = points
    data["streaks"] = streaks
    data["last_completed_days"] = last_completed
    ref.set(data)

update_streaks_and_points()

# Reward function
def get_reward(points):
    if points >= 300: return "Special family outing 🌟"
    if points >= 200: return "Movie night pick 🍿"
    if points >= 100: return "Extra screen time 30 min 🎮"
    if points >= 50: return "Ice cream treat 🍦"
    return "Keep going! Next at 50 points"

# ─── Admin Password (CHANGE THIS!) ───────────────────────────────────────────────
ADMIN_PASSWORD = "parent123"  # ← CHANGE THIS NOW

is_admin = False
with st.sidebar:
    st.markdown("**Parent Admin**")
    pw = st.text_input("Password", type="password", key="pw")
    if pw == ADMIN_PASSWORD:
        is_admin = True
        st.success("Admin OK")
    elif pw:
        st.error("Wrong password")

# ─── UI ──────────────────────────────────────────────────────────────────────────
st.title("Ruby & Sofia Chore Manager")
st.subheader(f"Today: {date.today().strftime('%A, %d %B %Y')}")

if is_admin:
    st.header("Admin Dashboard")

    col1, col2 = st.columns(2)

    with col1:
        for kid in data["kids"]:
            p = data["points"].get(kid, 0)
            s = data["streaks"].get(kid, 0)
            st.markdown(f"**{kid}** · Points: {p} · Streak: {s} 🔥")
            st.caption(f"Reward: {get_reward(p)}")

    with col2:
        kid = st.selectbox("Kid", data["kids"])
        adj = st.number_input("± Points", step=10, value=0)
        if st.button("Apply"):
            data["points"][kid] = data["points"].get(kid, 0) + adj
            ref.set(data)
            st.success(f"{kid} now has {data['points'][kid]} points")
            st.rerun()

        if st.button("Reset Everything"):
            if st.checkbox("Really reset?"):
                data["points"] = {"Ruby": 0, "Sofia": 0}
                data["streaks"] = {"Ruby": 0, "Sofia": 0}
                data["last_completed_days"] = {"Ruby": None, "Sofia": None}
                ref.set(data)
                st.success("Reset done")
                st.rerun()

    # Chores management
    chores = data.get("chores", [])
    new = st.text_input("New chore")
    if st.button("Add") and new.strip():
        if new.strip() not in chores:
            chores.append(new.strip())
            data["chores"] = chores
            ref.set(data)
            st.rerun()

    for c in chores[:]:
        cols = st.columns([4,1])
        cols[0].write(c)
        if cols[1].button("X", key=f"del_{c}"):
            chores.remove(c)
            data["chores"] = chores
            ref.set(data)
            st.rerun()

else:
    # Kid view
    if st.button("Generate New Assignments", type="primary"):
        ch = data["chores"][:]
        random.shuffle(ch)
        ass = {k: [] for k in data["kids"]}
        for i, chore in enumerate(ch):
            ass[data["kids"][i % 2]].append(chore)
        comp = {k: {c: False for c in tsk} for k, tsk in ass.items()}
        data.update({"last_assignments": ass, "completions": comp})
        ref.set(data)
        st.rerun()

    st.markdown("### Today's Chores")

    updated = False
    for kid in sorted(assignments):
        st.markdown(f"**★ {kid}**")
        for chore in sorted(assignments[kid]):
            key = f"{kid}_{chore.replace(' ','_')}"
            cur = completions.get(kid, {}).get(chore, False)
            done = st.checkbox(chore, value=cur, key=key)
            if done != cur:
                data["completions"].setdefault(kid, {})[chore] = done
                updated = True

    if updated:
        ref.set(data)
        update_streaks_and_points()
        st.success("Saved!")
        st.rerun()

# Progress
st.markdown("### Progress")
for kid in data["kids"]:
    p = data["points"].get(kid, 0)
    s = data["streaks"].get(kid, 0)
    st.markdown(f"{kid}: {p} pts · {s} day streak 🔥")
    st.caption(get_reward(p))

# Celebration
if assignments:
    total = sum(len(v) for v in assignments.values())
    done = sum(sum(v for v in c.values()) for c in completions.values())
    if total > 0 and done == total:
        st.balloons()
        st.markdown("### 🎉 ALL DONE TODAY! 🎉")
        st.markdown("Great job Ruby & Sofia! 🌟")

if st.button("Refresh"):
    st.rerun()

st.caption("Flynnchilada • Firebase • Add to home screen")