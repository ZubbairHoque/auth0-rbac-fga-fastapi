import os
import streamlit as st
import requests
from dotenv import load_dotenv

# Load configuration
# Note: Ensure .env is in the same directory or adjust path
load_dotenv(dotenv_path="frontend/.env")

# Reusable configuration
BACKEND_URL = os.getenv("backend_url", "http://localhost:8000")

# --- INITIALIZATION ---
# Ensure session state is prepared before any UI renders
if "authenticated_role" not in st.session_state:
    st.session_state["authenticated_role"] = None
if "user_id" not in st.session_state:
    st.session_state["user_id"] = None

def show_login_page():
    """Centered Login Card with professional layout."""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.title("🛡️ Secure Portal")
        st.write("Welcome. Please identify yourself to access your workspace.")
        st.divider()
        
        user_id_input = st.text_input("User ID:", placeholder="user:alice")    
        
        if st.button("Enter System", use_container_width=True):
            if not user_id_input:
                st.warning("Please enter a User ID.")
                return

            try:
                # Sequential role check: Admin first
                # This is the "B2B Sequential Knock" pattern
                with st.spinner("Validating permissions..."):
                    found_role = None
                    for role_type in ["admin", "member"]:
                        res = requests.get(
                            f"{BACKEND_URL}/dashboard/validate/{role_type}", 
                            params={"user_id": user_id_input}
                        )
                        if res.status_code == 200:
                            found_role = role_type
                            break
                    
                    if found_role:
                        st.session_state["authenticated_role"] = found_role
                        st.session_state["user_id"] = user_id_input
                        st.rerun()
                    else:
                        st.error("Access denied. No active roles assigned to this ID.")
            
            except requests.exceptions.ConnectionError:
                st.error("Connection failed. Is the backend server running?")
            except Exception as e:
                st.error(f"An unexpected error occurred: {str(e)}")

def show_admin_dashboard(user_id: str):
    """Dashboard for Administrative users."""
    st.sidebar.title("🛠️ Admin Menu")
    st.sidebar.info(f"**User:** {user_id}")
    
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    st.title("🚀 Admin Control Center")
    st.write("You have full visibility and management rights.")
    
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Users", "24")
    with col2:
        st.metric("Active Invitations", "3")
        
    if st.button("Generate System Audit Report"):
        st.success("Report generated! (Simulated)")

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
