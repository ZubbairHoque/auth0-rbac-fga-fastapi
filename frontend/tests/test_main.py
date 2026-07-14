from unittest.mock import MagicMock, patch, Mock
import app

@patch("app.st")
def test_empty_state(mock_st):
    """Test that the app renders an empty state when no role and user are set."""
    mock_st.session_state.return_value = None
    app.main()


@patch("app.st")
def test_admindb_call(mock_st):
    """Test that the admin dashboard calls the correct API endpoint."""
    
    mock_st.session_state.return_value = {
        "authenticated_role": "admin", "user_id": "user:alice"
    }
    
    mock_st.divider.return_value = None
    mock_st.columns.return_value = (MagicMock(), MagicMock())

    app.show_admin_dashboard("user:alice")

    app.main()

@patch("app.st")
def test_memberdb_call(mock_st):
    """Test that the member dashboard calls the correct API endpoint."""

    mock_st.session_state.return_value = {
        "authenticated_role": "member", "user_id": "user:alice"
    }
    
    mock_st.divider.return_value = None
    mock_st.columns.return_value = (MagicMock(), MagicMock())

    app.show_member_dashboard("user:alice")

    app.main()

@patch("app.st")
def test_invalid_role(mock_st):
    """Test that the app renders the login page when an invalid role is set."""
        
    session_data = {
        "authenticated_role": "invalid", "user_id": "user:alice"
    }

    mock_st.session_state = Mock(wraps=session_data)
    mock_st.button.return_value = True    


    app.main()
    
    mock_st.error.assert_called_once_with("Internal State Error: Unknown Role")
    mock_st.button.assert_called_once_with("Reset Session")
    mock_st.session_state.clear.assert_called_once()
    mock_st.rerun.assert_called_once()