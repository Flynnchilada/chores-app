# ─── IMPORTS ─────────────────────────────────────────────────────────────
import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import json
from datetime import date

# ─── CONFIG ─────────────────────────────────────────────────────────────
ADMIN_PASSWORD = "parent123"  # CHANGE THIS
SHARED_CHORE = "Clean Rooms"

today = date.today().isoformat()
today_display = date.today().strftime('%A, %d %B %Y')

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

    auto_assign_chores(data)

    ref.set(data)
    return data

# ─── Auto Assignment Logic ───────────────────────────────────────────────
def auto_assign_chores(data):
    kids = data["kids"]
    chores = data["chores"]

    # Remove shared chore from pool
    normal_chores = [c for c in chores if c != SHARED_CHORE]

    # Start clean
    data["assignments"] = {k: [] for k in kids}

    # Round-robin split
    for i, chore in enumerate(normal_chores):
        kid = kids[i % len(kids)]
        data["assignments"][kid].append(chore)

    # Add shared chore to everyone
    for kid in kids:
        if SHARED_CHORE not in data["assignments"][kid]:
            data["assignments"][kid].append(SHARED_CHORE)

# ─── Chore Toggle Logic ──────────────────────────────────────────────────
def on_chore_change(kid, chore, key):
    new_value = st.session_state.get(key, False)
    old_value = data.get("completions", {}).get(kid, {}).get(chore, False)

    data.setdefault("completions", {}).setdefault(kid, {})
    data["completions"][kid][chore] = new_value

    if new_value and not old_value:
        data["points"][kid] += 10
        st.toast(f"+10 points for {kid}", icon="⭐")

    ref.set(data)

# ─── UI ──────────────────────────────────────────────────────────────────
st.title("Ruby & Sofia Chore Manager")
st.subheader(f"Today: {today_display}")

data = get_data()

# ─── Parent Dashboard ────────────────────────────────────────────────────
st.markdown("---")
st.markdown("## 🔐 Parent Dashboard")

if st.checkbox("Parent Login"):
    password = st.text_input("Enter Parent Password", type="password")

    if password == ADMIN_PASSWORD:
        st.success("Parent Mode Active")

        # Add chore
        st.markdown("### ➕ Add Chore")
        new_chore = st.text_input("New chore name")

        if st.button("Add Chore"):
            new_chore = new_chore.strip()
            if not new_chore:
                st.error("Chore cannot be empty")
            elif new_chore in data["chores"]:
                st.warning("Chore already exists")
            else:
                data["chores"].append(new_chore)
                auto_assign_chores(data)
                ref.set(data)
                st.success(f"Added: {new_chore}")
                st.experimental_rerun()

        # Delete chore
        st.markdown("### ❌ Delete Chore")
        chore_to_delete = st.selectbox("Select chore", data["chores"])

        if st.button("Delete Chore"):
            data["chores"].remove(chore_to_delete)

            for kid in data["kids"]:
                data.get("completions", {}).get(kid, {}).pop(chore_to_delete, None)

            auto_assign_chores(data)
            ref.set(data)
            st.success(f"Deleted: {chore_to_delete}")
            st.experimental_rerun()

    elif password:
        st.error("Incorrect password")

# ─── Chore Display ───────────────────────────────────────────────────────
st.markdown("### Today's Chores")

for kid in data["kids"]:
    st.subheader(kid)

    chores = data["assignments"].get(kid, [])

    for chore in chores:
        key = f"{kid}_{chore}"
        st.checkbox(
            chore,
            value=data.get("completions", {}).get(kid, {}).get(chore, False),
            key=key,
            on_change=on_chore_change,
            args=(kid, chore, key)
        )

# ─── Progress ────────────────────────────────────────────────────────────
st.markdown("### Progress")

for kid in data["kids"]:
    pts = data["points"][kid]
    st.markdown(f"**{kid}** – ⭐ {pts} points")
    st.progress(min(pts / 300, 1.0))
    st.markdown("---")

st.caption("Flynnchilada • Firebase • Streamlit")