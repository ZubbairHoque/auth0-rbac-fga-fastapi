from unittest.mock import patch
from streamlit.testing.v1 import AppTest
import requests
import app

@patch("app.st")
def test_show_member_dashboard(mock_st):
    """Show user_id in sidebar and logout button."""

    mock_st.sidebar.return_value = None
    mock_st.info.return_value = None
    mock_st.sidebar.button.return_value=True

    app.show_member_dashboard("user:alice")
    
    # side bar assertions
    mock_st.sidebar.title.assert_called_with("📋 User Menu")
    mock_st.sidebar.info.assert_called_with("**User:** user:alice")
    mock_st.sidebar.button.assert_called_with("Logout", use_container_width=True)
    mock_st.session_state.clear.assert_called_once()
    mock_st.rerun.assert_called_once()

    # workspace assertions
    mock_st.title.assert_called_with("💼 Member Workspace")
    mock_st.info.assert_called_with("Your assigned resources and tasks will be listed here.")
    mock_st.write.assert_any_call("Currently, no tasks are pending.")
    mock_st.write.assert_any_call("Currently, no tasks are pending.")




