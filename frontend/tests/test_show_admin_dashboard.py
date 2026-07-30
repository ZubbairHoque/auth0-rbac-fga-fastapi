from unittest.mock import Mock, patch, MagicMock
from tests.test_show_login_page import _resp
import requests
import config
import views.admin

@patch("views.admin.st")
@patch("views.admin.requests.get")
def  test_dashboard_metrics(mock_requests, mock_st):
    """Should return and show metrics of members."""

    mock_st.divider.return_value = None
    mock_st.columns.return_value = (MagicMock(), MagicMock())

    fake_members = Mock()
    fake_members.status_code = 200

    fake_members.json.return_value = [
        {
            "id": "1", 
            "email": "alice@example.com", 
            "role": "admin", "status": "invited", 
            "created_at": "2023-01-01T00:00:00.000Z"
        },
        {
            "id": "2", 
            "email": "bob@example.com", 
            "role": "member", 
            "status": "active",
            "created_at": "2023-01-02T00:00:00.000Z"
        },
        {
            "id": "3", 
            "email": "charlie@example.com", 
            "role": "member", 
            "status": "removed", 
            "created_at": "2023-01-03T00:00:00.000Z"
        },
    ]

    mock_requests.return_value = fake_members

    views.admin.show_admin_dashboard("user:alice")

    assert mock_requests.call_args[0][0].endswith("/system/members")

    mock_st.metric.assert_any_call("Total Users:", 3)
    mock_st.metric.assert_any_call("Active Invitations:", 1)

@patch("views.admin.st")
@patch("builtins.print")
@patch("views.admin.requests.get")
def test_failed_to_load_member_connection_error(mock_requests, mock_print, mock_st):
    """Should log an exception for a connection error."""

    mock_st.divider.return_value = None
    mock_st.columns.return_value = (MagicMock(), MagicMock())

    mock_requests.side_effect = requests.exceptions.ConnectionError("Connection failed")
    views.admin.show_admin_dashboard("user:alice")

    # assert print statement
    mock_print.assert_any_call("Validation for admin role failed: Connection failed")
    mock_st.error.assert_any_call("Failed to load members")
    
@patch("views.admin.st")
@patch("views.admin.requests.get")
def test_dataframe_success(mock_requests, mock_st):
    """Should return and show metrics of members."""

    mock_st.divider.return_value = None
    mock_st.columns.return_value = (MagicMock(), MagicMock())

    fake_members = Mock()
    fake_members.status_code = 200

    fake_members.json.return_value = [
        {
            "id": "1", 
            "email": "alice@example.com", 
            "role": "admin", 
            "status": "invited", 
            "created_at": "2023-01-01T00:00:00.000Z"
        },
        {
            "id": "2", 
            "email": "bob@example.com", 
            "role": "member", 
            "status": "active", 
            "created_at": "2023-01-02T00:00:00.000Z"
        },
        {
            "id": "3", 
            "email": "charlie@example.com", 
            "role": "member", 
            "status": "removed", 
            "created_at": "2023-01-03T00:00:00.000Z"
        },
    ]

    mock_requests.return_value = fake_members
    
    views.admin.show_admin_dashboard("user:alice")

    actual_df = mock_st.dataframe.call_args[0][0] 

    assert actual_df.columns.tolist() == ["email", "role", "status", "created_at"] 
    
    assert len(actual_df) == 2
    assert actual_df.iloc[0].email == "alice@example.com"
    assert actual_df.iloc[1].role == "member"
    assert "removed" not in actual_df["status"].values

@patch("views.admin.st")
@patch("views.admin.requests.get")
@patch("views.admin.requests.delete")
@patch("views.admin.extract_error")
def test_remove_member(
    mock_extract, mock_delete, mock_requests, mock_st
):

    """Should verify that clicking 'Remove' initiates a DELETE request and reruns."""

    mock_requests.return_value = {"user_id": "user:alice"}

    # 1. Prevent the sidebar logout button from evaluating to True
    mock_st.button.return_value = False
    mock_st.sidebar.button.return_value = False

    # 2. Setup Streamlit layout mocks
    mock_st.divider.return_value = None
    mock_col1 = MagicMock()
    mock_col2 = MagicMock()

    # st.columns is called multiple times.
    mock_st.columns.side_effect = [
        (mock_col1, mock_col2),   # Metric columns
        (MagicMock(), mock_col2), # Alice's action columns
        (MagicMock(), mock_col2), # Bob's action columns
    ]

    # 3. Mock GET response for system members
    fake_members = Mock()
    fake_members.status_code = 200
    fake_members.json.return_value = [
        {
            "id": "1",
            "email": "alice@example.com",
            "role": "admin",
            "status": "invited",
            "created_at": "2023-01-01T00:00:00.000Z"
        },
        {
            "id": "2",
            "email": "bob@example.com",
            "role": "member",
            "status": "active",
            "created_at": "2023-01-02T00:00:00.000Z"
        },
        {
            "id": "3",
            "email": "charlie@example.com",
            "role": "member",
            "status": "removed",
            "created_at": "2023-01-03T00:00:00.000Z"
        },
    ]

    alice_id = fake_members.json.return_value[0].get("id")
    alice_role = fake_members.json.return_value[0].get("role")

    mock_requests.return_value = fake_members

    # 4. Simulate clicking "Remove" specifically for Alice
    mock_col2.button.side_effect = lambda *args, **kwargs: kwargs.get(
        "key"
    ) == "remove_1"

    # 5. Mock the backend API delete response
    fake_delete_resp = Mock()
    fake_delete_resp.status_code = 200
    mock_delete.return_value = fake_delete_resp

    # 6. Run the function
    views.admin.show_admin_dashboard("user:alice")

    # 7. Assertions
    actual_df = mock_st.dataframe.call_args[0][0]
    assert actual_df.columns.tolist() == ["email", "role", "status", "created_at"]
    assert len(actual_df) == 2

    success_calls = [call[0][0] for call in mock_st.success.call_args_list] # Success calls are in the form (message, key)
    
    assert "Removed alice@example.com successfully!" in success_calls
    mock_st.rerun.assert_called_once()


    assert "Removed bob@example.com successfully!" not in success_calls
    assert "Removed charlie@example.com successfully!" not in success_calls

    # assert st.rerun is called

    # Verify the API delete call was constructed correctly for Alice
    mock_delete.assert_called_once_with(
        f"{config.BACKEND_URL}/system/members/{alice_id}",
        params={
            "role": f"{alice_role}",
            "admin_user_id": "user:alice",
        },
    )


@patch("views.admin.st")
@patch("views.admin.requests.get")
def test_member_list_empty(mock_requests, mock_st):
    """Req 4.3: empty member list shows empty-state info message."""

    mock_st.divider.return_value = None
    mock_col1 = MagicMock()
    mock_col2 = MagicMock()
    mock_st.columns.return_value = (mock_col1, mock_col2)

    fake_members = Mock()
    fake_members.status_code = 200
    fake_members.json.return_value = []
    mock_requests.return_value = fake_members

    views.admin.show_admin_dashboard("user:alice")

    mock_st.info.assert_called_with("No active members found in the system")


@patch("views.admin.st")
@patch("views.admin.requests.get")
def test_all_removed(mock_requests, mock_st):
    """Req 4.4: all returned members removed -> empty df, no manage actions."""

    mock_st.divider.return_value = None
    mock_st.columns.return_value = (MagicMock(), MagicMock())

    fake_members = Mock()
    fake_members.status_code = 200
    fake_members.json.return_value = [
        {
            "id": "1",
            "email": "alice@example.com",
            "role": "admin",
            "status": "removed",
            "created_at": "2023-01-01T00:00:00.000Z",
        },
    ]
    mock_requests.return_value = fake_members

    views.admin.show_admin_dashboard("user:alice")

    actual_df = mock_st.dataframe.call_args[0][0]
    assert len(actual_df) == 0

    subheader_calls = [call[0][0] for call in mock_st.subheader.call_args_list]
    assert "Manage Members" not in subheader_calls

    info_calls = [call[0][0] for call in mock_st.info.call_args_list]
    assert "No active members found in the system" not in info_calls

@patch("views.admin.st")
@patch("views.admin.requests.get")
@patch("views.admin.requests.delete")
@patch("views.admin.extract_error")
def test_remove_member_extract_error(
    mock_extract, mock_delete, mock_requests, mock_st
):
    """
    When the delete response is not successful, THE test SHALL assert that the
    error message includes the value returned by `extract_error`.
    """
    # 1. Prevent the sidebar logout button from evaluating to True
    mock_st.sidebar.button.return_value = False
    mock_st.button.return_value = False

    # 2. Setup Streamlit layout mocks
    mock_st.divider.return_value = None
    mock_col1 = MagicMock()
    mock_col2 = MagicMock()

    # st.columns is called multiple times.
    mock_st.columns.side_effect = [
        (mock_col1, MagicMock()),   # Metric columns
        (MagicMock(), mock_col2),   # Alice's action columns
    ]

    mock_col2.button.side_effect = lambda *a, **kw: kw.get("key") == "remove_1"

    fake_members = Mock()
    fake_members.status_code = 200
    fake_members.json.return_value = [
        {
            "id": "1",
            "email": "alice@example.com",
            "role": "admin",
            "status": "invited",
            "created_at": "2023-01-01T00:00:00.000Z",
        }
    ]

    mock_requests.return_value = fake_members

    fake_delete_resp = Mock()
    fake_delete_resp.status_code = 400

    mock_delete.return_value = fake_delete_resp

    mock_extract.return_value = "Alice"

    views.admin.show_admin_dashboard("user:alice")

    mock_extract.assert_called_once_with(fake_delete_resp)  
    mock_st.error.assert_any_call("Failed to remove: Alice")  

@patch("views.admin.st")
@patch("views.admin.requests.get")
@patch("views.admin.requests.delete")
@patch("views.admin.extract_error")
def test_remove_member_connection_error(
    mock_extract, mock_delete, mock_requests, mock_st
):
    """Test that the backend connection failure message is displayed."""

    # 1. Prevent the sidebar logout button from evaluating to True
    mock_st.sidebar.button.return_value = False
    mock_st.button.return_value = False
    mock_st.form_submit_button.return_value = False


    # 2. Setup Streamlit layout mocks
    mock_st.divider.return_value = None
    mock_col1 = MagicMock()
    mock_col2 = MagicMock()

    # st.columns is called multiple times.
    mock_st.columns.side_effect = [
        (mock_col1, MagicMock()),   # Metric columns
        (MagicMock(), mock_col2),   # Alice's action columns
    ]

    mock_col2.button.side_effect = lambda *a, **kw: kw.get("key") == "remove_1"

    fake_members = Mock()
    fake_members.status_code = 200
    fake_members.json.return_value = [
        {
            "id": "1",
            "email": "alice@example.com",
            "role": "admin",
            "status": "invited",
            "created_at": "2023-01-01T00:00:00.000Z",
        }
    ]

    mock_requests.return_value = fake_members    

    mock_delete.side_effect = requests.exceptions.ConnectionError

    mock_extract.return_value = "Alice"
    views.admin.show_admin_dashboard("user:alice")
    mock_st.error.assert_called_once_with(
        "Connection failed. Is the backend server running?"
    )
    
@patch("views.admin.st")
@patch("views.admin.requests")
def test_invite_member_success( mock_requests, mock_st):
    """After invite form is submitted, invite should be sent with expected payload."""


    # 1. Prevent the sidebar logout button from evaluating to True
    mock_st.sidebar.button.return_value = False
    mock_st.button.return_value = False

    # 2. Setup Streamlit layout mocks
    mock_st.divider.return_value = None
    mock_col1 = MagicMock()
    mock_col2 = MagicMock()

    # st.columns is called multiple times.
    mock_st.columns.side_effect = [
        (mock_col1, MagicMock()),   # Metric columns
        (MagicMock(), mock_col2),   # Alice's action columns
    ]

    # render role selction
    mock_st.selectbox.return_value =["member", "admin"]

    # mock inputs
    mock_st.text_input.return_value = "alice@example.com"
    mock_st.selectbox.return_value = "member"
    mock_st.form_submit_button.return_value = True
    
    # mock get members
    fake_members = Mock()
    fake_members.status_code = 200
    fake_members.json.return_value = [
        {
            "id": "1",
            "email": "alice@example.com",
            "role": "admin",
            "status": "invited",
            "created_at": "2023-01-01T00:00:00.000Z",
        }
    ]

    mock_requests.get.return_value = fake_members

    mock_requests.post.return_value = _resp(200)

    mock_col2.button.return_value = False
    
    views.admin.show_admin_dashboard("user:alice")
    
    mock_requests.post.assert_called_once_with(
        f"{config.BACKEND_URL}/system/invite",
        params={"admin_user_id": "user:alice"},
        json={"email": "alice@example.com", "role": "member",},
    )

    mock_st.success.assert_called_once_with("Invitation sent successfully!")
    mock_st.rerun.assert_called_once()


@patch("views.admin.st")
@patch("views.admin.requests")
@patch("views.admin.extract_error")
def test_invite_member_extract_error(mock_extract, mock_requests, mock_st):
    """After invite form is submitted, status code 400 should be handled."""

    # 1. Prevent the sidebar logout button from evaluating to True
    mock_st.sidebar.button.return_value = False
    mock_st.button.return_value = False

    # 2. Setup Streamlit layout mocks
    mock_st.divider.return_value = None
    mock_col1 = MagicMock()
    mock_col2 = MagicMock()

    # st.columns is called multiple times.
    mock_st.columns.side_effect = [
        (mock_col1, MagicMock()),   # Metric columns
        (MagicMock(), mock_col2),   # Alice's action columns
    ]

    # render role selction
    mock_st.selectbox.return_value =["member", "admin"]

    # mock inputs
    mock_st.text_input.return_value = "alice@example.com"
    mock_st.selectbox.return_value = "member"
    mock_st.form_submit_button.return_value = True
    
    # mock get members
    fake_members = Mock()
    fake_members.status_code = 200
    fake_members.json.return_value = [
        {
            "id": "1",
            "email": "alice@example.com",
            "role": "admin",
            "status": "invited",
            "created_at": "2023-01-01T00:00:00.000Z",
        }
    ]

    mock_requests.get.return_value = fake_members

    fake_invite_resp = MagicMock()
    fake_invite_resp.status_code = 400

    mock_requests.post.return_value = fake_invite_resp
    mock_extract.return_value = "Alice"

    mock_col2.button.return_value = False
    
    views.admin.show_admin_dashboard("user:alice")
    
    mock_st.error.assert_called_once_with("Failed to invite: Alice")

@patch("views.admin.st")
@patch("views.admin.requests.post")
@patch("views.admin.requests.get")
@patch("views.admin.extract_error")
def test_invite_member_connection_error(mock_extract, mock_get, mock_post, mock_st):
    """After invite form is submitted, invite should be sent with expected payload."""


    # 1. Prevent the sidebar logout button from evaluating to True
    mock_st.sidebar.button.return_value = False
    mock_st.button.return_value = False

    # 2. Setup Streamlit layout mocks
    mock_st.divider.return_value = None
    mock_col1 = MagicMock()
    mock_col2 = MagicMock()

    # st.columns is called multiple times.
    mock_st.columns.side_effect = [
        (mock_col1, MagicMock()),   # Metric columns
        (MagicMock(), mock_col2),   # Alice's action columns
    ]

    # render role selction
    mock_st.selectbox.return_value =["member", "admin"]

    # mock inputs
    mock_st.text_input.return_value = "alice@example.com"
    mock_st.selectbox.return_value = "member"
    mock_st.form_submit_button.return_value = True
    
    # mock get members
    fake_members = Mock()
    fake_members.status_code = 200
    fake_members.json.return_value = [
        {
            "id": "1",
            "email": "alice@example.com",
            "role": "admin",
            "status": "invited",
            "created_at": "2023-01-01T00:00:00.000Z",
        }
    ]

    mock_get.return_value = fake_members

    mock_post.side_effect = requests.exceptions.ConnectionError

    mock_extract.return_value = "Alice"

    mock_col2.button.return_value = False
    
    views.admin.show_admin_dashboard("user:alice")

    mock_st.error.assert_called_once_with("Connection failed. Is the backend server running?")


@patch("views.admin.st")
@patch("views.admin.requests")
@patch("views.admin.extract_error")
def test_invite_member_empty_email(mock_extract, mock_requests, mock_st):
    """Invite member form should not submit if email is empty."""

    # 1. Prevent the sidebar logout button from evaluating to True
    mock_st.sidebar.button.return_value = False
    mock_st.button.return_value = False

    # 2. Setup Streamlit layout mocks
    mock_st.divider.return_value = None
    mock_col1 = MagicMock()
    mock_col2 = MagicMock()

    # st.columns is called multiple times.
    mock_st.columns.side_effect = [
        (mock_col1, MagicMock()),   # Metric columns
        (MagicMock(), mock_col2),   # Alice's action columns
    ]

    # render role selction
    mock_st.selectbox.return_value =["member", "admin"]

    # mock inputs
    mock_st.text_input.return_value = ""
    mock_st.selectbox.return_value = "member"
    mock_st.form_submit_button.return_value = True


    mock_col2.button.return_value = False
    
    views.admin.show_admin_dashboard("user:alice")
    
    mock_st.warning.assert_called_once_with("Email is required")
    mock_requests.assert_not_called()
    mock_st.error.assert_not_called()
