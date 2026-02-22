# ─── Parent Dashboard ────────────────────────────────────────────────────
st.markdown("---")
st.markdown("## 🔐 Parent Dashboard")

admin_mode = st.checkbox("Parent Login")

if admin_mode:
    password = st.text_input("Enter Parent Password", type="password")

    if password == ADMIN_PASSWORD:

        st.success("Parent Mode Active")

        if st.button("Reset All Points to 0"):
            for kid in data["kids"]:
                data["points"][kid] = 0
            ref.set(data)
            st.success("Points reset!")

        if st.button("Reset Today's Completions"):
            data["completions"] = {}
            data["daily_completions"][today] = {
                k: 0 for k in data["kids"]
            }
            ref.set(data)
            st.success("Today's completions reset!")

        if st.button("Reset EVERYTHING"):
            ref.set({})
            st.warning("Database cleared. Refresh app.")
            st.stop()

        selected_kid = st.selectbox("Select Kid", data["kids"])
        bonus = st.number_input("Points to Add", min_value=1, max_value=100, value=10)

        if st.button("Add Bonus Points"):
            data["points"][selected_kid] += bonus
            ref.set(data)
            st.success(f"Added {bonus} points to {selected_kid}!")

        # ─── Add New Chore ────────────────────────────────────────────────────
        st.markdown("### Add New Chore")

        new_chore = st.text_input("Enter a new chore", "")

        if st.button("Add Chore"):
            if new_chore:
                # Add the new chore to the list of chores for each kid
                for kid in data["kids"]:
                    if new_chore not in data["chores"]:
                        data["chores"].append(new_chore)
                ref.set(data)  # Update the Firebase database with the new chore
                st.success(f"New chore '{new_chore}' added!")
            else:
                st.error("Please enter a valid chore name.")
    elif password != "":
        st.error("Incorrect password")