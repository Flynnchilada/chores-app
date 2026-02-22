import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import random
import json
from datetime import date

# ─── Firebase Setup ──────────────────────────────────────────────────────────────
if 'firebase_initialized' not in st.session_state:
    st.session_state.firebase_initialized = False

if not st.session_state.firebase_initialized:
    st.write("Attempting to connect to Firebase...")  # visible feedback
    
    try:
        # 1. Check if secret exists
        if "firebase" not in st.secrets:
            raise KeyError("No 'firebase' section found in secrets")
            
        if "service_account_json" not in st.secrets["firebase"]:
            raise KeyError("No 'service_account_json' key found in secrets['firebase']")
        
        service_account_str = st.secrets["firebase"]["service_account_json"]
        st.write("Secret loaded (length:", len(service_account_str), "characters)")
        
        # 2. Parse JSON string → dict
        service_account_info = json.loads(service_account_str)
        st.write("JSON parsed successfully")
        
        # 3. Create credentials
        cred = credentials.Certificate(service_account_info)
        st.write("Credentials object created")
        
        # 4. Initialize
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://chores-1a1ac-default-rtdb.asia-southeast1.firebasedatabase.app/'
        })
        
        st.session_state.firebase_initialized = True
        st.success("Firebase connected successfully!")
        
    except KeyError as ke:
        st.error(f"Secrets configuration error: {ke}")
        st.error("Go to app Settings → Secrets and make sure you have:")
        st.code("""
[firebase]
service_account_json = '''
{ your full JSON here }
'''
        """)
        st.stop()
        
    except json.JSONDecodeError:
        st.error("Invalid JSON format in service_account_json secret")
        st.error("Make sure the JSON is valid and properly escaped (especially private_key line breaks)")
        st.stop()
        
    except Exception as e:
        st.error(f"Firebase initialization failed: {str(e)}")
        st.error("Common causes:")
        st.markdown("- Secret is missing or misspelled")
        st.markdown("- JSON has syntax error (missing comma, wrong quotes)")
        st.markdown("- Private key line breaks not preserved")
        st.stop()

# Database reference
DB_PATH = "/chores/ruby_sofia"
ref = db.reference(DB_PATH)

# ─── Load or Initialize Data ─────────────────────────────────────────────────────
@st.cache_data(ttl=10)  # refresh every 10 seconds
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

# Generate new assignments button
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
    st.rerun()  # refresh UI

# Display current assignments with checkboxes
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
        key = f"{kid}_{chore.replace(' ', '_')}"  # unique key for checkbox
        current_done = completions.get(kid, {}).get(chore, False)
        
        done = st.checkbox(
            chore,
            value=current_done,
            key=key
        )
        
        # Detect change
        if done != current_done:
            data.setdefault("completions", {}).setdefault(kid, {})[chore] = done
            updated = True

if updated:
    ref.set(data)
    st.success("Changes saved and synced!")
    st.rerun()

# Refresh button (for manual sync if needed)
if st.button("Refresh / Sync Now"):
    st.rerun()

# Status / info
if not assignments:
    st.info("No assignments yet. Click 'Generate New Assignments' to start!")
else:
    st.caption("Changes made by anyone will appear after refresh or next interaction.")

st.markdown("---")
st.caption("App by Flynnchilada • Data synced via Firebase • Add to home screen on iPhone for app-like experience")