# Frontend Test Plan

## Introduction

This plan defines the test coverage needed for `frontend/app.py` using tests under
`frontend/tests`. The frontend is a Streamlit application that authenticates a
typed user ID, renders admin and member dashboards, and calls backend APIs for
member listing, invitation, and removal.

The tests should validate frontend behavior without requiring a running backend
or manual browser interaction. Backend calls, Streamlit session state, and rerun
behavior must be mocked or exercised through Streamlit's test utilities.

## Scope

- Test target: `frontend/app.py`
- Test location: `frontend/tests`
- Test runner: `pytest`
- External dependencies to avoid in tests: live FastAPI backend, Auth0 FGA,
  network access, and persistent Streamlit state between tests

## Test Strategy

1. Use isolated tests for helper functions such as `extract_error`.
2. Use mocked `requests.get`, `requests.post`, and `requests.delete` calls for
   backend interactions.
3. Reset `st.session_state` between tests so authentication and dashboard tests
   do not leak state.
4. Prefer Streamlit app testing utilities where practical for end-to-end widget
   behavior. Use direct function calls with mocked Streamlit APIs only when the
   Streamlit test utility cannot cover a branch cleanly.
5. Assert both user-visible output and outbound backend request shape.

## Requirements

### ✅ Requirement 1: Test Error Extraction

**User Story:** As a developer, I want backend error handling covered, so that
frontend failures show useful messages.

> Completed: All 3 criteria covered and passing in `test_extract_error.py` —
> valid `detail`, invalid JSON, and JSON without `detail` (3 passed).

#### Acceptance Criteria

1. WHEN `extract_error` receives a response whose JSON body contains `detail`,
   THE test SHALL assert that the `detail` value is returned.
2. WHEN `extract_error` receives a response with invalid JSON, THE test SHALL
   assert that `response.text` is returned.
3. WHEN `extract_error` receives a JSON body without `detail`, THE test SHALL
   assert that `response.text` is returned.

---

### ✅ Requirement 2: Test Login Flow

**User Story:** As a user, I want login behavior covered, so that role detection
and access denial do not regress.

> Completed: All 5 criteria covered and passing in `test_show_login_page.py` — empty user ID, admin login, member login, invalid role, and connection error handling.

#### Acceptance Criteria

1. WHEN no user ID is submitted, THE test SHALL assert that the UI displays the
   "Please enter a User ID." warning and does not call the backend.
2. WHEN an entered user ID validates as `admin`, THE test SHALL assert that
   `/dashboard/validate/admin` is called before `/dashboard/validate/member`,
   session state stores `authenticated_role=admin`, and session state stores the
   submitted user ID.
3. WHEN admin validation fails and member validation succeeds, THE test SHALL
   assert that session state stores `authenticated_role=member`.
4. WHEN both role validations fail, THE test SHALL assert that the UI displays
   the access denied error and does not authenticate the user.
5. WHEN the validation request raises `requests.exceptions.ConnectionError`, THE
   test SHALL assert that the connection failure message is shown.

---

### ✅ Requirement 3: Test Admin Member Loading

**User Story:** As an admin, I want dashboard data loading covered, so that the
member summary remains accurate.

> Completed: All 4 criteria covered and passing in `test_show_admin_dashboard.py` — backend call verification, Total Users metric, Active Invitations metric, and connection error handling.

#### Acceptance Criteria

1. WHEN `show_admin_dashboard(user_id)` renders successfully, THE test SHALL
   assert that it calls `GET {BACKEND_URL}/system/members` with
   `admin_user_id=user_id`.
2. WHEN the backend returns members, THE test SHALL assert that "Total Users"
   equals the number of returned members.
3. WHEN the backend returns invited members, THE test SHALL assert that "Active
   Invitations" equals the number of members whose `status` is `invited`.
4. WHEN the backend request fails or raises during `raise_for_status`, THE test
   SHALL assert that "Failed to load members" is displayed and the dashboard
   continues rendering.

---

### ✅ Requirement 4: Test Admin Member Table

**User Story:** As an admin, I want the member table covered, so that the UI
shows the correct users and columns.

> Completed: All 4 criteria covered in `test_show_admin_dashboard.py` — column filtering, removed-member exclusion, empty-list info message, and all-removed empty dataframe with no manage actions (6 passed).

#### Acceptance Criteria

1. WHEN active or invited members are returned, THE test SHALL assert that the
   dataframe contains only the columns `email`, `role`, `status`, and
   `created_at`.
2. WHEN returned members include `status=removed`, THE test SHALL assert that
   removed members are excluded from the displayed dataframe.
3. WHEN the backend returns an empty member list, THE test SHALL assert that the
   empty-state message "No active members found in the system" is displayed.
4. WHEN all returned members are removed, THE test SHALL assert that the
   dataframe is empty or no removable member actions are rendered.

---

### ✅ Requirement 5: Test Remove Member Action

**User Story:** As an admin, I want member removal covered, so that revoke-access
actions call the backend correctly and surface failures.

> Completed: All 5 criteria covered and passing in `test_show_admin_dashboard.py` — keyed Remove button interaction (5.1), DELETE call with role/admin_user_id params (5.2), success message + single st.rerun (5.3), extract_error surfaced on non-200 (5.4), and delete ConnectionError message (5.5); 8 passed in file.

#### Acceptance Criteria

1. WHEN a non-removed member is displayed, THE test SHALL assert that a
   corresponding "Remove" button is rendered.
2. WHEN the remove button is clicked, THE test SHALL assert that the frontend
   calls `DELETE {BACKEND_URL}/system/members/{member_id}` with query params
   `role=<member role>` and `admin_user_id=<current admin user ID>`.
3. WHEN the delete response has status code `200`, THE test SHALL assert that a
   success message is displayed and `st.rerun` is requested.
4. WHEN the delete response is not successful, THE test SHALL assert that the
   error message includes the value returned by `extract_error`.
5. WHEN the delete request raises `requests.exceptions.ConnectionError`, THE
   test SHALL assert that the backend connection failure message is displayed.

---

### ✅ Requirement 6: Test Invite Member Form

**User Story:** As an admin, I want invitation behavior covered, so that new
member invites are sent with the expected payload.

> Completed: All 6 criteria covered and passing in `test_show_admin_dashboard.py` — POST payload with email/role/admin_user_id (6.1), success message + rerun on 200 (6.2), extract_error surfaced on non-200 (6.3), empty email warning with no POST (6.4), ConnectionError message (6.5), and role selector options verified (6.6); 12 passed in file.

#### Acceptance Criteria

1. WHEN the invite form is submitted with an email and role, THE test SHALL
   assert that the frontend calls `POST {BACKEND_URL}/system/invite` with query
   param `admin_user_id=<current admin user ID>` and JSON body containing
   `email` and `role`.
2. WHEN the invite response has status code `200`, THE test SHALL assert that
   "Invitation sent successfully!" is displayed and `st.rerun` is requested.
3. WHEN the invite response is not successful, THE test SHALL assert that the
   displayed error includes the backend-provided detail.
4. WHEN the invite form is submitted without an email, THE test SHALL assert
   that "Email is required" is displayed and no POST request is sent.
5. WHEN the invite request raises `requests.exceptions.ConnectionError`, THE
   test SHALL assert that the backend connection failure message is displayed.
6. WHEN the invite form renders, THE test SHALL assert that the role selector
   offers `admin` and `member`.

---

### ✅ Requirement 7: Test Member Dashboard

**User Story:** As a member, I want the member dashboard covered, so that the
non-admin experience remains available.

> Completed: All 3 criteria covered and passing in `test_show_member_dashboard.py` — sidebar user identification, workspace title/empty state display, and logout with session clear + rerun (1 passed).

#### Acceptance Criteria

1. WHEN `show_member_dashboard(user_id)` renders, THE test SHALL assert that the
   sidebar identifies the current user.
2. WHEN the member dashboard renders, THE test SHALL assert that it displays the
   member workspace title and pending-task empty state.
3. WHEN the logout button is clicked, THE test SHALL assert that session state
   is cleared and `st.rerun` is requested.

---

### Requirement 8: Test Main Routing

**User Story:** As a developer, I want top-level app routing covered, so that
session state consistently controls which page is rendered.

#### Acceptance Criteria

1. WHEN `authenticated_role` is `None`, THE test SHALL assert that `main()`
   renders the login page.
2. WHEN `authenticated_role` is `admin`, THE test SHALL assert that `main()`
   renders the admin dashboard with the stored user ID.
3. WHEN `authenticated_role` is `member`, THE test SHALL assert that `main()`
   renders the member dashboard with the stored user ID.
4. WHEN `authenticated_role` has an unknown value, THE test SHALL assert that
   the internal state error is displayed and reset behavior is available.

## Implementation Notes

- Add `frontend/tests/conftest.py` with fixtures for clearing Streamlit session
  state and monkeypatching backend requests.
- Use lightweight fake response objects with `status_code`, `json()`, `text`,
  and `raise_for_status()` methods.
- Patch `frontend.app.st.rerun` in tests so rerun requests can be asserted
  without interrupting the test process.
- Keep tests deterministic by setting `frontend.app.BACKEND_URL` explicitly in
  fixtures instead of depending on local environment variables.
- Do not use a live backend in frontend tests; backend behavior belongs in the
  backend test suite.
