import streamlit as st
import requests

from config import BACKEND_URL

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