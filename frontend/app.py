import streamlit as st
from views.login import show_login_page
from views.admin import show_admin_dashboard
from views.member import show_member_dashboard

# --- INITIALIZATION ---
# Ensure session state is prepared before any UI renders
if "authenticated_role" not in st.session_state:
    st.session_state["authenticated_role"] = None
if "user_id" not in st.session_state:
    st.session_state["user_id"] = None

def main():
    """Main application entry point."""
    # Set page configuration once
    st.set_page_config(page_title="B2B Secure Portal", page_icon="🛡️")
    
    role = st.session_state["authenticated_role"]
    user = st.session_state["user_id"]

    if role is None:
        show_login_page()
    elif role == "admin":
        show_admin_dashboard(user)
    elif role == "member":
        show_member_dashboard(user)
    else:
        st.error("Internal State Error: Unknown Role")
        if st.button("Reset Session"):
            st.session_state.clear()
            st.rerun()

if __name__ == "__main__":
    main()
