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
            "streaks": {"Ruby": 0, "Sofia": 0},          # new field
            "last_completed_days": {"Ruby": None, "Sofia": None}  # new field
        }
        ref.set(default_data)
        return default_data
    # Ensure streaks fields exist (for older data)
    if "streaks" not in data:
        data["streaks"] = {"Ruby": 0, "Sofia": 0}
    if "last_completed_days" not in data:
        data["last_completed_days"] = {"Ruby": None, "Sofia": None}
    return data

data = get_data()

# ─── Update Streaks Logic ────────────────────────────────────────────────────────
def update_streaks():
    today_str = date.today().isoformat()
    yesterday_str = (date.today() - timedelta(days=1)).isoformat()

    assignments = data.get("last_assignments", {})
    completions = data.get("completions", {})
    streaks = data.get("streaks", {"Ruby": 0, "Sofia": 0})
    last_completed = data.get("last_completed_days", {"Ruby": None, "Sofia": None})

    if not assignments:
        return  # no assignments today → no streak change

    total_chores = sum(len(tasks) for tasks in assignments.values())
    done_chores = sum(
        sum(1 for v in kid_compl.values() if v)
        for kid_compl in completions.values()
    )

    all_done_today = total_chores > 0 and done_chores == total_chores

    for kid in data["kids"]:
        last_day = last_completed.get(kid)
        current_streak = streaks.get(kid, 0)

        if all_done_today:
            if last_day == yesterday_str:
                # Continued streak
                current_streak += 1
            else:
                # New streak starts
                current_streak = 1
            last_completed[kid] = today_str
        else:
            # Failed to complete today → reset streak
            current_streak = 0
            # Do NOT change last_completed (keeps previous success for continuity)

        streaks[kid] = current_streak

    # Save back
    data["streaks"] = streaks
    data["last_completed_days"] = last_completed
    ref.set(data)

# Run streak update every load (safe because it's idempotent for today)
update_streaks()

# ─── App UI ──────────────────────────────────────────────────────────────────────
st.title("Ruby & Sofia Chore Manager")

today = date.today().strftime("%A, %d %B %Y")
st.subheader(f"Today: {today}")

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
    # Reset today's completion tracking for streaks
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
    update_streaks()  # re-check streaks after change
    st.success("Changes saved and synced!")
    st.rerun()

# ─── Show Streaks ────────────────────────────────────────────────────────────────
st.markdown("### Current Streaks 🔥")
for kid in data["kids"]:
    streak = data["streaks"].get(kid, 0)
    if streak > 0:
        emoji = "🔥" * min(streak, 5)  # max 5 flames for display
        st.markdown(f"**{kid}**: {streak} day{'s' if streak > 1 else ''} in a row! {emoji}")
    else:
        st.markdown(f"**{kid}**: 0 days — let's start a streak today! 💪")

# Celebration if all done today
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
            <div style="text-align: center; font-size: 2.8em; color: #2ecc71; margin: 40px 0;">
            🎉 ALL DONE TODAY! 🎉
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown(
            "<p style='text-align: center; font-size: 1.4em; color: #27ae60;'>"
            "You're absolute legends Ruby & Sofia! 🌟✨ Keep the streak going!"
            "</p>",
            unsafe_allow_html=True
        )

# Manual refresh
if st.button("Refresh / Sync Now"):
    st.rerun()

if not assignments:
    st.info("No assignments yet. Click 'Generate New Assignments' to start!")
else:
    st.caption("Changes appear after refresh or interaction.")

st.markdown("---")
st.caption("App by Flynnchilada • Synced via Firebase • Add to iPhone home screen")