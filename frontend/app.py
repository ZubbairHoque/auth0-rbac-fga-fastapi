import os
from dotenv import load_dotenv
import streamlit as st
import requests

# Load environment variables
load_dotenv(dotenv_path="frontend/.env")

# Reusable configuration
BACKEND_URL = os.getenv("backend_url", "http://localhost:8000")

# Initialize session state
if "authenticated_role" not in st.session_state:
    st.session_state["authenticated_role"] = None
if "user_id" not in st.session_state:
    st.session_state["user_id"] = None

# --- APP LOGIC ---

if st.session_state["authenticated_role"] is None:
    # --- SHOW LOGIN UI ---
    st.title("Login")
    
    user_id_input = st.text_input("User ID:", placeholder="user:alice")    
    login_clicked = st.button("Enter")

    if login_clicked:
        if not user_id_input:
            st.warning("Please enter a User ID.")
        else:
            try:
                # 1. Check Admin Access
                admin_res = requests.get(
                    f"{BACKEND_URL}/dashboard/validate/admin", 
                    params={"user_id": user_id_input}
                )
                
                if admin_res.status_code == 200:
                    st.session_state["authenticated_role"] = "admin"
                    st.session_state["user_id"] = user_id_input
                    st.rerun()

                # 2. If not admin, check Member Access
                # Note: Backend uses singular 'member'
                elif admin_res.status_code == 403:
                    member_res = requests.get(
                        f"{BACKEND_URL}/dashboard/validate/member", 
                        params={"user_id": user_id_input}
                    )

                    if member_res.status_code == 200:
                        st.session_state["authenticated_role"] = "member"
                        st.session_state["user_id"] = user_id_input
                        st.rerun()
                    else:
                        st.error("Access denied. You do not have an assigned role.")
                
            except requests.exceptions.ConnectionError:
                st.error(
                    "Unable to connect to the backend. Is the FastAPI server running?"
                    )

else:
    # --- SHOW DASHBOARD UI ---
    role = st.session_state["authenticated_role"]
    user = st.session_state["user_id"]

    st.sidebar.title("Navigation")
    st.sidebar.write(f"**Logged in as:** {user}")
    st.sidebar.write(f"**Role:** {role.capitalize()}")
    
    if st.sidebar.button("Logout"):
        st.session_state["authenticated_role"] = None
        st.session_state["user_id"] = None
        st.rerun()

    st.title(f"{role.capitalize()} Dashboard")
    
    if role == "admin":
        st.subheader("Administrative Overview")
        st.write(
            """
            Welcome to the control center. Here you can manage system-wide settings.
            """
            )
        
        # Example Admin Widget
        if st.button("Generate System Audit Report"):
            st.info("Generating report... (Placeholder)")
            
    elif role == "member":
        st.subheader("Member Workspace")
        st.write("Welcome back! Here are the resources assigned to you.")
        
        # Example Member Widget
        st.info("No active tasks found.")
