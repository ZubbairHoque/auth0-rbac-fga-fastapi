from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.modules.resource.model import ResourceDB
from app.core.database import get_db, init_db
from app.modules.resource.routes import router as resource_routes
from app.modules.auth_fga.routes import router as auth_fga_routes
from app.modules.member.routes import router as member_routes
from app.modules.auth_fga.service import authz_service
from app.core import security

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown events."""
    # 1. Initialize Database
    print(f"Starting {settings.app_title} v{settings.app_version}")
    print("Initializing database...")
    await init_db()

    # 2. Pre-fetch Auth0 public keys (The Speed Boost)
    # Since this hits the network, we do it at startup so the cache is hot.
    print("Pre-fetching Auth0 public keys...")
    try:
        security.jwks_client.get_signing_keys()
    except Exception as e:
        print(f"Warning: Could not pre-fetch Auth0 keys: {e}")

    # 3. Check Auth0 FGA connection
    fga_healthy = await authz_service.check_auth0_fga_health()
    if fga_healthy:
        print("Auth0 FGA connection established!")
    else:
        print("Warning: Auth0 FGA connection failed.")

    yield


app = FastAPI(
    title="Auto Texting",
    version=settings.app_version,
    lifespan=lifespan,
    description="""
    A reusable single-tenant internal application template using FastAPI and Auth0 FGA.
    """
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(resource_routes, prefix="/resources", tags=["resources"])
app.include_router(auth_fga_routes, prefix="/auth", tags=["auth_fga"])
app.include_router(member_routes, prefix="/members", tags=["members"])

@app.get("/")
async def read_root():
    return {
        "message": "Welcome to your Single-Tenant Internal App",
        "docs": "/docs"
    }

@app.get("/items")
async def read_items(db: AsyncSession = Depends(get_db)):
    """Example endpoint to read items from the database."""
    result = await db.execute(select(ResourceDB))
    items = result.scalars().all()
    return items
