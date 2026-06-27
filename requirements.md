# Requirements Document

## Introduction

This feature completes the admin member management flow for a single-tenant FastAPI + Auth0 FGA application. The backend has partial scaffolding (models, invite route, webhook, members list route) but contains bugs and missing pieces. The Streamlit frontend admin dashboard is fully stubbed with hardcoded data. This spec covers fixing the existing broken logic, adding the missing `DELETE /system/members/{member_id}` route, and wiring the frontend admin dashboard to live backend APIs.

## Glossary

- **System**: The FastAPI backend application
- **Admin**: A user with the `admin` role in Auth0 FGA, allowed to manage members
- **Member**: A user with the `member` role in Auth0 FGA
- **MemberDB**: The SQLAlchemy database model storing member identity and lifecycle state
- **InvitationDB**: The SQLAlchemy database model storing pending email invitations
- **FGA**: Auth0 Fine-Grained Authorization service storing role tuples
- **Webhook**: The `POST /system/auth/webhook/post-registration` endpoint triggered by Auth0 after a user registers
- **Dashboard**: The Streamlit frontend admin UI at `frontend/app.py`

---

## Requirements

### ✅ Requirement 1: Fix POST /system/invite Response

> Completed: `/invite` now returns a single `Invitation` (role from body only) and creates a matching `MemberDB(status=invited)`; verified by `test_invite_user_success`.

**User Story:** As an admin, I want to invite a new user by email and role, so that they receive a pending invitation and appear in the member list.

#### Acceptance Criteria

1. WHEN an admin sends a valid `POST /system/invite` request with an `InvitationCreate` body, THE System SHALL return a single `Invitation` object matching the `response_model=Invitation` declaration
2. WHEN the invite endpoint is called, THE System SHALL derive the invited role from `InvitationCreate.role` only, removing the redundant `role` query parameter
3. IF an admin sends `POST /system/invite` without a valid JSON body, THEN THE System SHALL return HTTP 422
4. WHEN an invitation is created, THE System SHALL also create a corresponding `MemberDB` record with `status=invited` and the same email and role

---

### ✅ Requirement 2: Fix Webhook Member Activation

> Completed: Webhook updates invitation and member in a single transaction, and handles missing member records gracefully without error.

**User Story:** As a new user who registered via an invite link, I want my account to be activated automatically, so that I appear as an active member in the admin dashboard.

#### Acceptance Criteria

1. WHEN the webhook receives a valid registration payload for an email with a pending invitation, THE System SHALL set `MemberDB.auth0_user_id = payload.user_id`
2. WHEN the webhook activates a member, THE System SHALL set `MemberDB.status = MemberStatus.active`
3. WHEN the webhook activates a member, THE System SHALL commit both the invitation update and the member update in the same transaction
4. IF no `MemberDB` record exists for the invited email at webhook time, THEN THE System SHALL still complete the FGA assignment and invitation mark-as-used without error

---

### ✅ Requirement 3: Add DELETE /system/members/{member_id}

> Completed: Added route with proper status handling for active/invited members, omitting FGA calls for unassigned users, and enforcing soft-delete.

**User Story:** As an admin, I want to remove a member from the system, so that they lose access and the dashboard reflects their removal.

#### Acceptance Criteria

1. WHEN an admin sends `DELETE /system/members/{member_id}` for an active or invited member, THE System SHALL set `MemberDB.status = MemberStatus.removed`
2. WHEN removing a member whose `status` is `active`, THE System SHALL also call `authz.remove_user_role` to delete the FGA role tuple
3. WHEN removing a member whose `status` is `invited`, THE System SHALL set status to `removed` without calling FGA (no tuple exists yet)
4. IF the `member_id` does not exist in `MemberDB`, THEN THE System SHALL return HTTP 404
5. IF the requesting `admin_user_id` does not have `can_manage_users` permission, THEN THE System SHALL return HTTP 403
6. WHEN a member is removed, THE System SHALL NOT delete the `MemberDB` row (soft delete for audit history)

---

### ✅ Requirement 4: Fix Test Suite

> Completed: Fixed async test session hygiene and added full coverage for DELETE /system/members endpoints including active, invited, 404, and 403 scenarios.

**User Story:** As a developer, I want a passing test suite, so that regressions are caught automatically.

#### Acceptance Criteria

1. WHEN `test_invite_user_success` runs, THE System SHALL send a valid `InvitationCreate` JSON body and assert on the returned `Invitation` fields
2. WHEN any test in `test_system_routes.py` uses `db_session.commit()`, THE System SHALL use `await db_session.commit()` to avoid async session errors
3. WHEN the `DELETE /system/members/{member_id}` route exists, THE System SHALL have tests covering: admin success (active member), admin success (invited member), 404 not found, and 403 forbidden

---

### Requirement 5: Live Admin Dashboard Metrics

**User Story:** As an admin, I want the dashboard to show real member counts and an active invitations count, so that I can understand the current system state at a glance.

#### Acceptance Criteria

1. WHEN the admin dashboard loads, THE Dashboard SHALL call `GET /system/members?admin_user_id={user_id}` and display the count of non-removed members as "Total Users"
2. WHEN the admin dashboard loads, THE Dashboard SHALL derive and display the count of members with `status=invited` as "Active Invitations"
3. IF the backend call fails, THEN THE Dashboard SHALL display an error message instead of crashing

---

### Requirement 6: Member Table in Admin Dashboard

**User Story:** As an admin, I want to see a table of all current members and their status, so that I can understand who has access and who has a pending invite.

#### Acceptance Criteria

1. WHEN the admin dashboard loads, THE Dashboard SHALL render a table with columns: email, role, status, created_at
2. THE Dashboard SHALL display only members with `status != removed` (relying on the backend filter)
3. WHEN no members exist, THE Dashboard SHALL display an appropriate empty-state message

---

### Requirement 7: Invite Form in Admin Dashboard

**User Story:** As an admin, I want to invite a new member from the dashboard, so that I do not need to use the API directly.

#### Acceptance Criteria

1. WHEN an admin submits the invite form with a valid email and role, THE Dashboard SHALL call `POST /system/invite?admin_user_id={user_id}` with a JSON body `{"email": ..., "role": ...}`
2. WHEN the invite succeeds, THE Dashboard SHALL display a success message and refresh the member list
3. IF the invite fails (e.g., duplicate email, network error), THEN THE Dashboard SHALL display the error message from the backend response
4. WHEN the invite form is displayed, THE Dashboard SHALL provide a role selector with options `admin` and `member`

---

### Requirement 8: Remove Member Action in Admin Dashboard

**User Story:** As an admin, I want to remove a member from the dashboard, so that I can revoke access without using the API directly.

#### Acceptance Criteria

1. WHEN the member table is rendered, THE Dashboard SHALL display a "Remove" button for each non-removed member
2. WHEN an admin clicks "Remove" for a member, THE Dashboard SHALL call `DELETE /system/members/{member_id}?admin_user_id={user_id}`
3. WHEN the removal succeeds, THE Dashboard SHALL display a success message and refresh the member list
4. IF the removal fails, THEN THE Dashboard SHALL display the error message from the backend response
