import streamlit as st

def show_member_dashboard(user_id: str):
    """Dashboard for standard users."""
    st.sidebar.title("📋 User Menu")
    st.sidebar.info(f"**User:** {user_id}")
    
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    st.title("💼 Member Workspace")
    st.write("Welcome back to your workspace.")
    
    st.info("Your assigned resources and tasks will be listed here.")
    st.write("Currently, no tasks are pending.")