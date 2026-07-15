# FastAPI OpenFGA RBAC Demo

This project demonstrates how to implement **Role-Based Access Control (RBAC)** using OpenFGA with FastAPI. It follows OpenFGA's best practices for coarse-grained access control, starting simple and building up complexity gradually.

## RBAC Model Overview

This demo implements a simple organizational RBAC pattern with:

- **Organizations**: Groups that contain users with specific roles
- **Users**: Individual actors with roles in organizations  
- **Resources**: Assets owned by organizations
- **Roles**: `admin` and `member` with different permission levels

## OpenFGA Model

```yaml
type user

type organization
  relations
    define admin: [user]
    define member: [user]
    
    define can_add_member: admin
    define can_delete_member: admin
    define can_view_member: admin or member
    define can_add_resource: admin or member

type resource
  relations
    define organization: [organization]
    
    define can_delete_resource: admin from organization
    define can_view_resource: admin from organization or member from organization
```

## Key RBAC Concepts Demonstrated

### 1. **Direct Role Assignment**
- Users are directly assigned `admin` or `member` roles in organizations

### 2. **Permission Inheritance**
- Resource permissions inherit from organization roles
- Uses OpenFGA's `from` keyword to map organization roles to resource permissions
- `admin from organization` means "users who are admins of the organization that owns this resource"

### 3. **Persistent Data Storage**
- Uses SQLite database with SQLAlchemy for data persistence
- Data survives server restarts unlike in-memory storage
- ACID compliance ensures data integrity

## Permission Matrix

| Role | Add Members | Delete Members | View Members | Add Resources | Delete Resources | View Resources |
|------|-------------|----------------|--------------|---------------|------------------|----------------|
| **admin** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **member** | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ |

## Project Structure

```
fastapi-openfga-project/
├── app/
│   ├── main.py                  # FastAPI application entry point
│   ├── config.py                # Configuration settings
│   ├── database.py              # SQLAlchemy database setup and models
│   ├── models/
│   │   ├── organization.py      # Organization Pydantic models
│   │   └── resource.py          # Resource Pydantic models
│   ├── routes/
│   │   ├── organization_routes.py # Organization management endpoints
│   │   └── resource_routes.py   # Resource management endpoints
│   ├── services/
│   │   └── authorization_service.py # OpenFGA integration
│   ├── utils/
│   │   └st_security.py` — HMAC valid/invalid, JWT valid/invalid (parametrized)
- [x] `test_utils_auth0_fg_client.py` — lazy init, check, write, delete, list, health check

### Frontend
- [x] Streamlit login page with sequential role validation
- [x] `show_member_dashboard()` — stub member workspace view

---

## What's Still TODO

### Backend — Bugs & Missing Logic

- [ ] **`POST /system/invite` returns a tuple, not a valid response**
  - `return (new_inv, new_member)` is not a valid `Invitation` response model — should return `new_inv` only (or a combined schema)
  - `role` is accepted as both a query param and inside `InvitationCreate`, creating a conflict; consolidate to one source of truth

- [ ] **Webhook does not update `MemberDB` on registration**
  - `sync_user_to_fga` marks the invitation used and writes the FGA tuple, but never sets `MemberDB.auth0_user_id` or flips `status` to `active`
  - Add: find matching `MemberDB` by email → set `auth0_user_id = payload.user_id` → set `status = MemberStatus.active` → commit

- [ ] **`DELETE /system/members/{member_id}` route is missing**
  - `DELETE /system/users/{user_id}` removes a FGA tuple by `user_id` string but has no DB side-effect
  - Need a proper `DELETE /system/members/{member_id}` that: checks admin permission → removes FGA role for active members → sets `MemberDB.status = removed`

- [ ] **`test_invite_user_success` is broken**
  - Calls `POST /system/invite` with no request body (missing `InvitationCreate` JSON)
  - Assertion checks for `"Successfully synced"` which is the webhook message, not the invite response
  - Fix the test to POST a valid `{"email": "...", "role": "..."}` body and assert on the returned `Invitation` object

- [ ] **`conftest.py` `db_session` fixture uses sync `commit()`**
  - `db_session.commit()` should be `await db_session.commit()` — async sessions require awaited commits
  - Same for `db_session.add()` followed by `db_session.commit()` in `test_system_routes.py`

- [ ] **`hmac.new(...)` should be `hmac.new(...)` → `verify_signature` uses `hmac.new` not `hmac.HMAC`**
  - `security.py` calls `hmac.new(...)` — the correct call is `hmac.new(key=..., msg=..., digestmod=...)` which is valid but double-check this runs without error on the target Python version (3.10+)

### Backend — Missing Routes

- [ ] **`DELETE /system/members/{member_id}`** (see above)
- [ ] **`GET /system/members/{member_id}`** — optional but useful for the frontend detail view

### Frontend — Admin Dashboard

- [ ] **Replace hardcoded metrics with live API calls**
  - `Total Users` and `Active Invitations` are static strings `"24"` and `"3"`
  - Call `GET /system/members?admin_user_id={user_id}` and derive counts from the response

- [ ] **Add member table**
  - Fetch members list and render with `st.dataframe` or `st.table`
  - Show: email, role, status, created_at
  - Filter out removed members by default (backend already does this)

- [ ] **Add invite form**
  - Input: email + role selector (`admin` / `member`)
  - On submit: `POST /system/invite?admin_user_id={user_id}` with JSON body `{"email": ..., "role": ...}`
  - Show success/error feedback and refresh member list

- [ ] **Add remove/delete member action**
  - Per-row delete button in the member table
  - Call `DELETE /system/members/{member_id}?admin_user_id={user_id}` once that route exists
  - Show confirmation before delete

---

## Setup

### Initial Setup (First Time Only)

**Create the virtual environment at the project root:**

```powershell
# From project root
uv venv .venv
```

**Activate the virtual environment:**

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate
```

**Install backend dependencies:**

```powershell
# With venv activated, from the backend directory
cd backend
uv sync --active --inexact --native-tls
```

**Configure backend:**

```bash
cd backend
cp .env.example .env
# Fill in Auth0 FGA credentials in .env
```

### Virtual Environment Management

**⚠️ Important: This project uses a single `.venv` at the project root.**

**Activate from project root:**

```powershell
# Windows
.\.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate
```

**Activate from `backend/` or `frontend/`:**

```powershell
# Windows
..\.venv\Scripts\Activate.ps1

# macOS/Linux
source ../.venv/bin/activate
```

**Deactivate:**

```powershell
deactivate
```

**⚠️ Avoid creating `backend/.venv`:**

- **DO NOT** run `uv sync` or `uv venv` from inside `backend/` — this will create `backend/.venv`
- **DO** use `python -m pytest`, `python -m uvicorn`, etc. after activating the root `.venv`
- **DO** use `cd backend` then `uv sync --active --inexact --native-tls` with the venv activated

### Running the Backend

**From project root:**

```powershell
.\.venv\Scripts\Activate.ps1
cd backend
python -m uvicorn app.main:app --reload
```

**From `backend/` directly:**

```powershell
..\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

### Running the Frontend

```bash
cd frontend
# Ensure BACKEND_URL is set in frontend/.env
streamlit run app.py
```

### Running Tests

**From project root:**

```powershell
.\.venv\Scripts\Activate.ps1
cd backend
python -m pytest tests/ -v
```

**From `backend/` directly:**

```powershell
..\.venv\Scripts\Activate.ps1
python -m pytest tests/ -v
```

**Run specific test file:**

```powershell
python -m pytest tests/test_resource_route.py -v
```

**⚠️ Note:** Use `python -m pytest`, not bare `pytest`. This ensures pytest runs from the active venv.

---

## Environment Variables

| Variable | Description |
|---|---|
| `AUTH0_FGA_DOMAIN` | Your Auth0 domain |
| `AUTH0_FGA_STORE_ID` | FGA store ID |
| `AUTH0_FGA_CLIENT_ID` | FGA client credentials ID |
| `AUTH0_FGA_CLIENT_SECRET` | FGA client credentials secret |
| `AUTH0_FGA_AUTHORIZATION_MODEL_ID` | FGA model ID |
| `AUTH0_FGA_API_TOKEN_ISSUER` | Token issuer URL |
| `AUTH0_FGA_API_AUDIENCE` | API audience |
| `AUTH0_FGA_API_URL` | FGA API base URL |
| `WEBHOOK_SIGNATURE_SECRET` | HMAC secret for Auth0 webhook verification |
| `DATABASE_URL` | SQLAlchemy async DB URL (default: `sqlite+aiosqlite:///./app.db`) |

---

## Key Design Decisions

- **FGA is authorization-only** — it answers "is this user allowed?", not "who are my users?". Member identity lives in `MemberDB`; FGA holds only role tuples.
- **Soft deletes** — removed members stay in `MemberDB` with `status=removed` for audit history; they are excluded from the default member list query.
- **Invitation flow** — `POST /invite` creates both an `InvitationDB` (with a token) and a pending `MemberDB`. The Auth0 post-registration webhook activates the member by linking their `auth0_user_id` and flipping status to `active`.
- **No Alembic yet** — tables are created via `Base.metadata.create_all` at startup. Migration support should be added before any schema changes in production.
