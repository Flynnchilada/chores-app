# ─── IMPORTS ─────────────────────────────────────────────────────────────
import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import json
from datetime import date

# ─── CONFIG ─────────────────────────────────────────────────────────────
ADMIN_PASSWORD = "parent123"  # CHANGE THIS

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
        "Feed dog", "Feed cat", "Clean kitty litter",
        "Put away dishes", "Put away clothes",
        "Take out rubbish bins", "Wipe kitchen bench"
    ])
    data.setdefault("assignments", {k: [] for k in data["kids"]})
    data.setdefault("completions", {})
    data.setdefault("points", {k: 0 for k in data["kids"]})

    ref.set(data)
    return data

data = get_data()

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

# ─── Parent Dashboard ────────────────────────────────────────────────────
st.markdown("---")
st.markdown("## 🔐 Parent Dashboard")

if st.checkbox("Parent Login"):
    password = st.text_input("Enter Parent Password", type="password")

    if password == ADMIN_PASSWORD:
        st.success("Parent Mode Active")

        # ─── Add Chore ────────────────────────────────────────────────
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
                ref.set(data)
                st.success(f"Added: {new_chore}")

        # ─── Delete Chore ─────────────────────────────────────────────
        st.markdown("### ❌ Delete Chore")
        chore_to_delete = st.selectbox("Select chore", data["chores"])

        if st.button("Delete Chore"):
            data["chores"].remove(chore_to_delete)

            for kid in data["kids"]:
                data["assignments"][kid].remove(chore_to_delete) \
                    if chore_to_delete in data["assignments"][kid] else None
                data.get("completions", {}).get(kid, {}).pop(chore_to_delete, None)

            ref.set(data)
            st.success(f"Deleted: {chore_to_delete}")
            st.experimental_rerun()

        # ─── Assign Chores ────────────────────────────────────────────
        st.markdown("### 👧 Assign Chores Per Child")

        selected_kid = st.selectbox("Select Child", data["kids"])
        selected_chore = st.selectbox("Select Chore", data["chores"])

        if st.button("Assign Chore"):
            if selected_chore not in data["assignments"][selected_kid]:
                data["assignments"][selected_kid].append(selected_chore)
                ref.set(data)
                st.success(f"Assigned {selected_chore} to {selected_kid}")

        if st.button("Unassign Chore"):
            if selected_chore in data["assignments"][selected_kid]:
                data["assignments"][selected_kid].remove(selected_chore)
                data.get("completions", {}).get(selected_kid, {}).pop(selected_chore, None)
                ref.set(data)
                st.success(f"Unassigned {selected_chore} from {selected_kid}")

    elif password:
        st.error("Incorrect password")

# ─── Chore Display ───────────────────────────────────────────────────────
st.markdown("### Today's Chores")

for kid in data["kids"]:
    st.subheader(kid)

    chores = data["assignments"].get(kid, [])

    if not chores:
        st.info("No chores assigned today")
        continue

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