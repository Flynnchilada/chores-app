# ─── IMPORTS (MUST BE FIRST) ─────────────────────────────────────────────
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
        "Feed dog", "Do dog poo", "Feed cat", "Clean kitty litter",
        "Put away dishes", "Put away clean clothes",
        "Take out rubbish bins", "Wipe kitchen bench"
    ])
    data.setdefault("completions", {})
    data.setdefault("points", {"Ruby": 0, "Sofia": 0})
    data.setdefault("daily_completions", {})
    data.setdefault("badges", {"Ruby": [], "Sofia": []})

    ref.set(data)
    return data

data = get_data()

# ─── Helpers ────────────────────────────────────────────────────────────
def get_level(points):
    if points >= 300: return "Level 4 – Superstar 🌟"
    if points >= 200: return "Level 3 – Champion 🏆"
    if points >= 100: return "Level 2 – Rising Hero 🚀"
    return "Level 1 – Starter 🌱"

# ─── Chore Checkbox Logic ────────────────────────────────────────────────
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

        # ─── Add Chore ───────────────────────────────────────────────────
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

        # ─── Delete Chore ────────────────────────────────────────────────
        st.markdown("### ❌ Delete Chore")

        if data["chores"]:
            chore_to_delete = st.selectbox(
                "Select chore to delete",
                data["chores"]
            )

            if st.button("Delete Chore"):
                # Remove from chore list
                data["chores"].remove(chore_to_delete)

                # Remove from all completions
                for kid in data["kids"]:
                    if kid in data.get("completions", {}):
                        data["completions"][kid].pop(chore_to_delete, None)

                ref.set(data)
                st.success(f"Deleted chore: {chore_to_delete}")
                st.experimental_rerun()
        else:
            st.info("No chores to delete")

    elif password:
        st.error("Incorrect password")

# ─── Chore List ──────────────────────────────────────────────────────────
st.markdown("### Today's Chores")

for kid in data["kids"]:
    st.subheader(kid)
    for chore in data["chores"]:
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
    pts = data["points"].get(kid, 0)
    st.markdown(f"**{kid}** · {get_level(pts)}")
    st.progress(min(pts / 400, 1.0))
    st.markdown("---")

st.caption("Flynnchilada • Firebase • Streamlit")