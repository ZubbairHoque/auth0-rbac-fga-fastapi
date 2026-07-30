import os
import streamlit as st
import pandas as pd
import requests
from dotenv import load_dotenv

# Load configuration
# Note: Ensure .env is in the same directory or adjust path
load_dotenv(dotenv_path="frontend/.env")

# Reusable configuration
BACKEND_URL = os.getenv("backend_url", "http://localhost:8000")


def extract_error(response):
    """Return the backend-provided error detail, falling back to raw text."""
    try:
        payload = response.json()
        if isinstance(payload, dict) and "detail" in payload:
            return payload["detail"]
    except Exception:
        pass
    return response.text

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
    
    try:
        res = requests.get(
            f"{BACKEND_URL}/system/members",
            params={"admin_user_id": user_id }       
        )

        res.raise_for_status()
        members = res.json()

    except Exception as e:
        print(f"Validation for admin role failed: {e}")
        st.error("Failed to load members")
        members = []

    # 2. Calculate your counts here!
    total_users = len(members)
    active_invites = sum([1 for m in members if m.get("status") == "invited"])
    
    st.write("You have full visibility and management rights.")
    
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Users:", total_users)
    with col2:
        st.metric("Active Invitations:", active_invites)

    st.subheader("Member Info Table:")
    

    if members:
        # Render table if we have members:

        # 1. Filter out the removed members
        active_members = [
            m for m in members if m.get("status") != "removed"
        ]

        # 2. Convert the filtered list of dictionaries into a Pandas DataFrame
        df = pd.DataFrame(active_members)

        # 3. Clean up the columns
        if not df.empty:
            df =  df[["email", "role", "status", "created_at"]]

        # 4. show member info
        st.dataframe(df, use_container_width=True)

    else:
        # Empty state message
        st.info("No active members found in the system")

    # --- Manage members (remove) ---
    if members:
        manageable = [m for m in members if m.get("status") != "removed"]
        if manageable:
            st.subheader("Manage Members")
            for member in manageable:
                col_label, col_action = st.columns([4, 1])
                col_label.write(f"{member.get('email')} ({member.get('role')})")

                if col_action.button("Remove", key=f"remove_{member.get('id')}"):
                    try:
                        with st.spinner("Removing member..."):
                            res = requests.delete(
                                f"{BACKEND_URL}/system/members/{member.get('id')}",
                                params={
                                    "role": member.get("role"),
                                    "admin_user_id": user_id,
                                },
                            )

                        if res.status_code == 200:
                            st.success(
                                f"Removed {member.get('email')} successfully!"
                            )
                            st.rerun()
                        else:
                            st.error(f"Failed to remove: {extract_error(res)}")

                    except requests.exceptions.ConnectionError:
                        st.error("Connection failed. Is the backend server running?")
                    except Exception as e:
                        st.error(f"An unexpected error occurred: {str(e)}")


    if st.button("Generate System Audit Report"):
        st.success("Report generated! (Simulated)")

    with st.form("invite_member_form"):
        st.subheader("Invite New Member")
        new_email = st.text_input("Email Address")
        new_role = st.selectbox("Assign Role", ["admin", "member"])

        # Submit Button:
        submitted = st.form_submit_button("Send Invitation")

        if submitted:
            if new_email:
                try:
                    with st.spinner("Sending invitation..."):
                        res = requests.post(
                            f"{BACKEND_URL}/system/invite",
                            params={"admin_user_id": user_id},
                            json={
                                "email": new_email,
                                "role": new_role,
                            },
                        )

                    if res.status_code == 200:
                        st.success("Invitation sent successfully!")
                        st.rerun()
                    else:
                        st.error(f"Failed to invite: {extract_error(res)}")

                except requests.exceptions.ConnectionError:
                    st.error("Connection failed. Is the backend server running?")
                except Exception as e:
                    st.error(f"An unexpected error occurred: {str(e)}")
            else:
                st.warning("Email is required")

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
