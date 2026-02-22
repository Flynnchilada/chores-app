import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import random
from datetime import date

# Firebase setup (use same service account JSON)
if not firebase_admin._apps:    
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://chores-1a1ac-default-rtdb.asia-southeast1.firebasedatabase.app/'
    })

DB_PATH = "/chores/ruby_sofia"
ref = db.reference(DB_PATH)

# Load or init data
data = ref.get() or {
    "kids": ["Ruby", "Sofia"],
    "chores": ["Feed dog", "Do dog poo", "Feed cat", "Clean kitty litter", "Put away dishes", "Put away clean clothes", "Take out rubbish bins", "Wipe kitchen bench"],
    "last_date": None,
    "last_assignments": None,
    "completions": {}
}

st.title("Ruby & Sofia Chore Manager")

today = date.today().strftime("%A, %d %B %Y")
st.subheader(f"Today: {today}")

if st.button("Generate New Assignments"):
    chores_copy = data["chores"][:]
    random.shuffle(chores_copy)
    assignments = {kid: [] for kid in data["kids"]}
    for i, chore in enumerate(chores_copy):
        kid = data["kids"][i % len(data["kids"])]
        assignments[kid].append(chore)
    completions = {kid: {chore: False for chore in tasks} for kid, tasks in assignments.items()}
    data["last_date"] = today
    data["last_assignments"] = assignments
    data["completions"] = completions
    ref.set(data)
    st.success("New assignments generated & synced!")

# Display assignments with checkboxes
assignments = data.get("last_assignments", {})
completions = data.get("completions", {})

for kid in sorted(assignments):
    st.markdown(f"**★ {kid}**")
    tasks = assignments.get(kid, [])
    for chore in sorted(tasks):
        key = f"{kid}_{chore}"
        done = completions.get(kid, {}).get(chore, False)
        if st.checkbox(chore, value=done, key=key):
            if not done:
                data["completions"].setdefault(kid, {})[chore] = True
                ref.set(data)
                st.toast(f"Marked: {chore} ✓")

if not assignments:
    st.info("No assignments yet — generate new ones!")

# Auto-refresh for real-time (Streamlit reruns on interaction; use st.experimental_rerun() in thread if needed)
st.caption("Changes sync live across devices!")