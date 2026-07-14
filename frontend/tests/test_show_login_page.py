from unittest.mock import Mock, patch, MagicMock
import requests
import app

def _resp(status):
    r = Mock(); r.status_code = status; return r

@patch("app.st")
@patch("app.requests.get")
def test_admin_login(mock_requests, mock_st):
    """Should return True for a valid role."""

    mock_st.columns.return_value = (MagicMock(), MagicMock(), MagicMock())

    mock_st.text_input.return_value = "user:alice"
    mock_st.button.return_value = True

    mock_requests.return_value = _resp(200)

    app.show_login_page()
    
    assert mock_requests.call_args[0][0].endswith("/dashboard/validate/admin")

    mock_st.session_state.__setitem__.assert_any_call("authenticated_role", "admin")
    mock_st.session_state.__setitem__.assert_any_call("user_id", "user:alice")

@patch("app.st")
@patch("app.requests.get")
def test_member_login(mock_requests, mock_st):
    """Should return True for a member role."""

    mock_st.columns.return_value = (MagicMock(), MagicMock(), MagicMock())
    mock_st.text_input.return_value = "user:alice"
    mock_st.button.return_value = True

    mock_requests.side_effect = [_resp(403), _resp(200)]
    app.show_login_page()

    urls = [call[0][0] for call in mock_requests.call_args_list]
    assert urls[0].endswith("/dashboard/validate/admin")
    assert urls[1].endswith("/dashboard/validate/member")

    mock_st.session_state.__setitem__.assert_any_call("authenticated_role", "member")
    mock_st.session_state.__setitem__.assert_any_call("user_id", "user:alice")

@patch("app.st")
@patch("app.requests.get")
def test_invalid_role_forbidden(mock_requests, mock_st, ):
    """Should return False for an invalid role."""

    mock_st.columns.return_value = (MagicMock(), MagicMock(), MagicMock())
    mock_st.text_input.return_value = "user:alice"
    mock_st.button.return_value = True

    mock_requests.return_value = _resp(403)
    app.show_login_page()

    mock_st.error.assert_called_with(
        "Access denied. No active roles assigned to this ID."
    )

@patch("app.st")
@patch("app.requests.get")
def test_empty_user_id(mock_requests, mock_st, caplog):
    """Should log an exception for an empty user ID."""

    mock_st.columns.return_value = (MagicMock(), MagicMock(), MagicMock())
    mock_st.text_input.return_value = ""
    mock_st.button.return_value = True
    
    app.show_login_page()
    mock_st.warning.assert_called_with("Please enter a User ID.")
        
@patch("app.st")
@patch("app.requests.get")
def test_connection_error(mock_requests, mock_st):
    """Should log an exception for a connection error."""

    mock_st.columns.return_value = (MagicMock(), MagicMock(), MagicMock())
    mock_st.text_input.return_value = "user:alice"
    mock_st.button.return_value = True

    # Session was called with admin role, but the backend is down, so it should raise a connection error
    mock_requests.side_effect = requests.exceptions.ConnectionError
    app.show_login_page()

    mock_st.error.assert_called_with(
        "Connection failed. Is the backend server running?"
    ) 
  
