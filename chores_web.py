import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import random
import json
from datetime import date, timedelta

# ─── CONFIG ─────────────────────────────────────────────────────────────────────
TEAM_CHORES = ["Clean Rooms", "Tidy Playroom", "Family Clean-up", "Garden Watering"]  # ← Add more team chores here

ADMIN_PASSWORD = "parent123"  # ← CHANGE THIS TO SOMETHING ONLY YOU KNOW!

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
    st.error("Check Settings → Secrets → firebase → service_account_json")
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
    ref.set(data)
    return data

data = get_data()

# Early definitions (prevents NameError)
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

    for kid in data["kids"]:
        kid_done = sum(1 for v in completions.get(kid, {}).values() if v)
        points[kid] += kid_done * 10
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

update_streaks_and_points()

# ─── Reward function ─────────────────────────────────────────────────────────────
def get_reward(points):
    if points >= 300: return "Special family outing 🌟"
    if points >= 200: return "Movie night pick 🍿"
    if points >= 100: return "Extra screen time 30 min 🎮"
    if points >= 50:  return "Ice cream treat 🍦"
    return "Keep going! Next at 50 points"

# ─── Admin check ─────────────────────────────────────────────────────────────────
is_admin = False
with st.sidebar:
    st.markdown("**Parent Admin**")
    pw = st.text_input("Password", type="password", key="pw")
    if pw == ADMIN_PASSWORD:
        is_admin = True
        st.success("Admin access granted")
    elif pw:
        st.error("Wrong password")

# ─── Main UI ─────────────────────────────────────────────────────────────────────
st.title("Ruby & Sofia Chore Manager")
st.subheader(f"Today: {today_display}")

if is_admin:
    st.header("Admin Dashboard (Parent Only)")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Current Status")
        for kid in data["kids"]:
            p = data["points"].get(kid, 0)
            s = data["streaks"].get(kid, 0)
            st.markdown(f"**{kid}**")
            st.markdown(f"Points: **{p}**")
            st.markdown(f"Streak: **{s}** days 🔥")
            st.caption(f"Reward: {get_reward(p)}")
            st.markdown("---")

    with col2:
        st.subheader("Manual Adjustments")
        kid = st.selectbox("Select kid", data["kids"], key="adj_kid")
        adj = st.number_input("± Points (negative to remove)", value=0, step=10, key="adj_val")

        if st.button("Apply Points Change", key="btn_apply"):
            if adj != 0:
                data["points"][kid] = data["points"].get(kid, 0) + adj
                ref.set(data)
                st.success(f"{adj:+} points → {kid} now has **{data['points'][kid]}**")
                st.rerun()

        if st.button("Reset Everything", key="btn_reset"):
            if st.checkbox("Confirm reset?", key="chk_reset"):
                data["points"] = {"Ruby": 0, "Sofia": 0}
                data["streaks"] = {"Ruby": 0, "Sofia": 0}
                data["last_completed_days"] = {"Ruby": None, "Sofia": None}
                ref.set(data)
                st.success("Reset complete")
                st.rerun()

    # Manage chores
    st.subheader("Manage Chores List")
    chores = data.get("chores", [])

    new_chore = st.text_input("Add new chore", key="new_chore")
    if st.button("Add Chore", key="btn_add") and new_chore.strip():
        c = new_chore.strip()
        if c not in chores:
            chores.append(c)
            data["chores"] = chores
            ref.set(data)
            st.success(f"Added: **{c}**")
            st.rerun()

    st.write("Current chores:")
    for c in chores:
        cols = st.columns([5, 1])
        cols[0].write(c)
        if cols[1].button("Remove", key=f"del_{c}"):
            chores.remove(c)
            data["chores"] = chores
            ref.set(data)
            st.rerun()

else:
    # Kid view
    if st.button("Generate New Assignments", type="primary"):
        ch = data["chores"][:]
        random.shuffle(ch)

        team_chores = [c for c in ch if c in TEAM_CHORES]
        individual_chores = [c for c in ch if c not in TEAM_CHORES]

        ass = {kid: [] for kid in data["kids"]}

        # Team chores assigned to BOTH kids
        for chore in team_chores:
            for kid in data["kids"]:
                ass[kid].append(chore)

        # Individual chores distributed randomly
        for i, chore in enumerate(individual_chores):
            ass[data["kids"][i % len(data["kids"])]].append(chore)

        comp = {kid: {c: False for c in tasks} for kid, tasks in ass.items()}

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
            st.info("No chores today – nice break!")
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
        st.success("Changes saved and synced!")
        st.rerun()

# ─── Progress & Rewards ──────────────────────────────────────────────────────────
st.markdown("### Progress & Rewards")
for kid in data["kids"]:
    p = data["points"].get(kid, 0)
    s = data["streaks"].get(kid, 0)
    st.markdown(f"**{kid}**")
    st.markdown(f"🔥 Streak: **{s}** day{'s' if s != 1 else ''}")
    st.markdown(f"⭐ Points: **{p}**")
    st.progress(min(p / 300, 1.0), text=f"Next reward: {get_reward(p)}")
    st.caption(f"Reward unlocked: {get_reward(p)}")
    st.markdown("---")

# ─── Celebration ─────────────────────────────────────────────────────────────────
if assignments:
    total = sum(len(v) for v in assignments.values())
    done = sum(sum(1 for v in c.values() if v) for c in completions.values())
    if total > 0 and done == total:
        st.balloons()
        st.markdown(
            "<h2 style='text-align:center; color:#2ecc71'>🎉 ALL DONE TODAY! 🎉</h2>",
            unsafe_allow_html=True
        )
        st.markdown(
            "<p style='text-align:center; font-size:1.4em; color:#27ae60'>"
            "You're absolute legends Ruby & Sofia! 🌟 Keep the streak going!"
            "</p>",
            unsafe_allow_html=True
        )

if st.button("Refresh / Sync Now"):
    st.rerun()

if not assignments:
    st.info("No assignments yet. Click 'Generate New Assignments' to start!")

st.markdown("---")
st.caption("App by Flynnchilada • Synced via Firebase • Add to iPhone home screen")