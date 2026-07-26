# Requirements: Modular Monolith Refactor

## 1. Goal

Refactor `backend/app` from a **layered architecture** (models/, routes/, services/, utils/) to a **modular monolith** organised by **business domain** under `app/modules/`.

> [!NOTE]
> **Status:** COMPLETED :tada:
> All tests pass (51/51) and the old layered directories have been safely removed.

---

## 2. Previous Architecture (Before)

```
backend/app/
├── main.py
├── config.py
├── database.py
├── __init__.py
├── fga/
│   └── model.fga.yaml
├── models/
│   ├── resource.py
│   ├── member.py
│   └── invitation.py
├── routes/
│   ├── resource_routes.py
│   ├── system_routes.py
│   └── dashboard_routes.py
├── services/
│   └── authorization_service.py
└── utils/
    ├── auth0_fga_client.py
    └── security.py
```

> [!NOTE]
> **What's wrong with the current structure?**
> The current layout groups files by **technical layer** (models, routes, services). This works for small apps, but as complexity grows, a single route file like `system_routes.py` ends up owning logic for members, invitations, webhooks, and role assignment — all unrelated concerns packed together. The modular approach groups files by **what they do in the business**, not what technical role they play.

---

## 3. Current Architecture (After Migration)

```
backend/app/
├── main.py                         # App factory & lifespan
├── __init__.py
├── core/                           # Shared infrastructure
│   ├── __init__.py
│   ├── config.py                   # ← from app/config.py
│   ├── database.py                 # ← from app/database.py (Base, engine, session ONLY)
│   └── security.py                 # ← from app/utils/security.py (JWT + HMAC, cross-cutting)
│
└── modules/
    ├── __init__.py
    │
    ├── resource/                   # Resource domain
    │   ├── __init__.py
    │   ├── model.py                # ← SQLAlchemy: ResourceDB
    │   ├── schema.py               # ← Pydantic: Resource schemas
    │   └── routes.py               # ← from app/routes/resource_routes.py
    │
    ├── member/                     # Member + Invite domain
    │   ├── __init__.py
    │   ├── model.py                # ← SQLAlchemy: MemberDB, InvitationDB
    │   ├── schema.py               # ← Pydantic: Member, Invitation, Auth0RegistrationPayLoad
    │   └── routes.py               # ← member/invite routes extracted from system_routes.py (includes webhook)
    │
    └── auth_fga/                   # FGA authorization domain
        ├── __init__.py
        ├── client.py               # ← from app/utils/auth0_fga_client.py (renamed)
        ├── service.py              # ← from app/services/authorization_service.py (renamed)
        ├── routes.py               # ← role assignment, dashboard validation, health check
        └── model.fga.yaml          # ← from app/fga/model.fga.yaml
```

---

## 4. Module Specifications

### 4.1 `app/core/` — Shared Infrastructure

| File | Source | Contents |
|------|--------|----------|
| `config.py` | `app/config.py` | `Settings` class, `settings` singleton |
| `database.py` | `app/database.py` | Engine, session factory, `Base`, `get_db`, `init_db`. **(SQLAlchemy models move out)** |
| `security.py` | `app/utils/security.py` | `verify_signature`, `verify_auth0_token`, `jwks_client`, plus `get_current_user` dependency |

> [!TIP]
> **Design tip — The dependency direction test.**
> Ask yourself: *"If I deleted the `auth_fga` module entirely, would this code still make sense?"* JWT verification and HMAC signatures are general security primitives — they'd exist even without FGA. That confirms they're infrastructure, not domain logic. `core/` is correct.

---

### 4.2 `app/modules/resource/` — Resource Domain

| File | Source | Responsibility |
|------|--------|----------------|
| `model.py` | Extracted from `database.py` | SQLAlchemy: `ResourceDB` |
| `schema.py` | `app/models/resource.py` | Pydantic: `ResourceBase`, `ResourceCreate`, `ResourceUpdate`, `Resource` |
| `routes.py` | `app/routes/resource_routes.py` | CRUD endpoints: `GET /`, `GET /{id}`, `POST /`, `DELETE /{id}` |

---

### 4.3 `app/modules/member/` — Member & Invitation Domain

| File | Source | Responsibility |
|------|--------|----------------|
| `model.py` | Extracted from `database.py` | SQLAlchemy: `MemberDB`, `InvitationDB` |
| `schema.py` | `app/models/member.py` + `app/models/invitation.py` | Pydantic schemas for Member and Invitation. Includes `MemberStatus`, `Role`, `Auth0RegistrationPayLoad` |
| `routes.py` | Extracted from `app/routes/system_routes.py` | Routes that manage member lifecycle + invitation flow |

**Routes to extract into `member/routes.py`:**

| Route | Current location | Why it belongs here |
|-------|-----------------|---------------------|
| `DELETE /members/{member_id}` | `system_routes.py` L62–103 | Directly manages member status transitions |
| `POST /invite` | `system_routes.py` L105–145 | Creates an invitation and a pending member |
| `POST /auth/webhook/post-registration` | `system_routes.py` L148–193 | Activates a member after registration (consumes invitation) |
| `GET /members` | `system_routes.py` L195–210 | Lists members |

> [!IMPORTANT]
> **Design tip — The webhook route is the hardest call.**
> `POST /auth/webhook/post-registration` touches both member activation **and** FGA role assignment. It lives at the seam between the `member` and `auth_fga` domains. We put it in `member/` — that's defensible because the **primary entity being mutated** is the member record. The FGA call is a side-effect. A good rule of thumb: *"The module that owns the data being written owns the route."*

---

### 4.4 `app/modules/auth_fga/` — FGA Authorization Domain

| File | Source | Responsibility |
|------|--------|----------------|
| `client.py` | `app/utils/auth0_fga_client.py` | `Auth0FGAClient` class, `fga_client` singleton |
| `service.py` | `app/services/authorization_service.py` | `AuthorizationService` class, `authz_service` singleton |
| `routes.py` | Extracted from `system_routes.py` + all of `dashboard_routes.py` | Routes focused on authorization checks and role management |
| `model.fga.yaml` | `app/fga/model.fga.yaml` | OpenFGA authorization model definition |

**Routes to extract into `auth_fga/routes.py`:**

| Route | Current location | Why it belongs here |
|-------|-----------------|---------------------|
| `POST /users` (assign role) | `system_routes.py` L45–60 | Pure FGA role assignment, no member/invite data |
| `GET /validate/{dashboard_type}` | `dashboard_routes.py` L10–25 | Pure FGA permission check |
| `GET /health` | `main.py` L69–76 | FGA health check — move out of `main.py` |

---

## 5. Decomposition of `system_routes.py`

This is the most complex file to break apart. Here's the full mapping:

```mermaid
graph LR
    SR["system_routes.py<br/>(210 lines)"] --> M["member/routes.py"]
    SR --> A["auth_fga/routes.py"]
    
    SR -->|"L62-103: DELETE /members/id"| M
    SR -->|"L105-145: POST /invite"| M
    SR -->|"L148-193: POST /auth/webhook"| M
    SR -->|"L195-210: GET /members"| M
    SR -->|"L45-60: POST /users"| A
    
    DR["dashboard_routes.py<br/>(26 lines)"] -->|"L10-25: GET /validate/type"| A
    
    MAIN["main.py L69-76:<br/>GET /system/health"] -->|health check| A
```

---

## 6. Import Path Changes

All internal imports must be updated. Key changes:

| Old Import | New Import |
|------------|------------|
| `from app.config import settings` | `from app.core.config import settings` |
| `from app.database import get_db, ResourceDB, ...` | `from app.core.database import get_db` and `from app.modules.resource.model import ResourceDB` |
| `from app.utils.security import ...` | `from app.core.security import ...` |
| `from app.utils.auth0_fga_client import fga_client` | `from app.modules.auth_fga.client import fga_client` |
| `from app.services.authorization_service import ...` | `from app.modules.auth_fga.service import ...` |
| `from app.models.resource import ...` | `from app.modules.resource.schema import ...` |
| `from app.models.member import ...` | `from app.modules.member.schema import ...` |
| `from app.models.invitation import ...` | `from app.modules.member.schema import ...` |

---

## 7. `main.py` Updates

After the refactor, `main.py` should:

1. Import routers from modules:
   ```python
   from app.modules.resource.routes import router as resource_router
   from app.modules.member.routes import router as member_router
   from app.modules.auth_fga.routes import router as auth_fga_router
   ```

2. Register routers with appropriate prefixes:
   ```python
   app.include_router(resource_router, prefix="/resources", tags=["resources"])
   app.include_router(member_router, prefix="/members", tags=["members"])
   app.include_router(auth_fga_router, prefix="/auth", tags=["authorization"])
   ```

3. Remove the inline `GET /system/health` and `GET /items` endpoints.

4. Update lifespan imports to use `app.core.*` and `app.modules.auth_fga.*`.

> [!TIP]
> **Design tip — Prefix strategy.**
> Your current prefixes (`/system`, `/dashboard`) are implementation-oriented. With modules, you have a chance to make them API-consumer-oriented: `/members`, `/resources`, `/auth`. Think about what makes sense from the perspective of someone reading your OpenAPI docs. The URL should tell you *what you're acting on*, not *which internal system handles it*.

---

---

## 8. Migration Completion Checklist

- [x] Create `app/core/` and move infrastructure files.
- [x] Create `app/modules/resource/` and extract models/schemas/routes.
- [x] Create `app/modules/auth_fga/` and configure service & client.
- [x] Create `app/modules/member/` and extract member/invite routes.
- [x] Extract remaining `system_routes.py` logic.
- [x] Update `main.py` router registration.
- [x] Update all test suites and fix dependency overrides.
- [x] Tests pass successfully (51/51).
- [x] Delete old legacy directories.

---

## 9. Phase 2: Test Architecture Refactor

### 9.1 Goal
Mirror the modular monolith structure in the `backend/tests/` directory to make tests easier to find and maintain. Tests should be grouped by the domain they verify rather than sitting in a flat list.

### 9.2 Target Test Architecture

```
backend/tests/
├── conftest.py
├── test_main.py
├── core/
│   ├── test_db.py
│   └── test_security.py
└── modules/
    ├── resource/
    │   └── test_resource_routes.py (renamed from test_resource_route.py)
    ├── member/
    │   └── test_member_routes.py (extracted from test_system_routes.py)
    └── auth_fga/
        ├── test_authorization_service.py
        ├── test_client.py (renamed from test_utils_auth0_fg_client.py)
        └── test_auth_routes.py (extracted from test_dashboard_routes.py & auth routes in test_system_routes.py)
```

### 9.3 Migration Steps

1. **Core Infrastructure Tests:** Create `backend/tests/core/` and move `test_db.py` and `test_security.py`.
2. **Resource Module Tests:** Create `backend/tests/modules/resource/` and move `test_resource_route.py` (rename it to `test_resource_routes.py`).
3. **Auth FGA Module Tests:** Create `backend/tests/modules/auth_fga/` and move `test_authorization_service.py` and `test_utils_auth0_fg_client.py` (rename to `test_client.py`).
4. **Member Module Tests:** Create `backend/tests/modules/member/` and extract member-related tests (e.g., invites, webhooks, member removal) from `test_system_routes.py` into a new `test_member_routes.py`.
5. **Auth Routes Tests:** Extract the FGA role assignment and dashboard tests from `test_system_routes.py` and `test_dashboard_routes.py` into `backend/tests/modules/auth_fga/test_auth_routes.py`.
6. **Cleanup:** Delete `test_dashboard_routes.py` and `test_system_routes.py`.
7. **Verification:** Run `pytest tests/ -v` to ensure all 51 tests still pass!
