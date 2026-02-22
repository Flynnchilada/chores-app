import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import random
import json
from datetime import date

# ─── Firebase Setup ──────────────────────────────────────────────────────────────
# Only initialize once per browser session
if 'firebase_app' not in st.session_state:
    try:
        # Load secret
        service_account_str = st.secrets["firebase"]["service_account_json"]
        service_account_info = json.loads(service_account_str)

        cred = credentials.Certificate(service_account_info)

        # Initialize with a unique name to be extra safe (even though one is enough)
        app = firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://chores-1a1ac-default-rtdb.asia-southeast1.firebasedatabase.app/'
        }, name='chores-app')

        st.session_state.firebase_app = app

    except Exception as e:
        st.error("Firebase connection failed")
        st.error(str(e))
        st.error("Please verify the 'firebase' → 'service_account_json' secret in app Settings.")
        st.stop()

# Use the initialized app
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
            "completions": {}
        }
        ref.set(default_data)
        return default_data
    return data

data = get_data()

# ─── App UI ──────────────────────────────────────────────────────────────────────
st.title("Ruby & Sofia Chore Manager")

today = date.today().strftime("%A, %d %B %Y")
st.subheader(f"Today: {today}")

# Generate new assignments
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

    ref.set(data)
    st.success("New assignments created and synced!")
    st.rerun()

# Display chores
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
    st.success("Changes saved and synced!")
    st.rerun()

# Manual refresh
if st.button("Refresh / Sync Now"):
    st.rerun()

if not assignments:
    st.info("No assignments yet. Click 'Generate New Assignments' to start!")
else:
    st.caption("Changes made by anyone will appear after refresh or next interaction.")

st.markdown("---")
st.caption("App by Flynnchilada • Data synced via Firebase • Add to home screen on iPhone")