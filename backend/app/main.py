from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import ResourceDB, get_db, init_db
from app.routes import resource_routes, system_routes, dashboard_routes
from app.services.authorization_service import authz_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"Starting {settings.app_title} v{settings.app_version}")
    print("Initializing database...")
    await init_db()

    # Check Auth0 FGA connection
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
app.include_router(resource_routes.router, prefix="/resources", tags=["resources"])
app.include_router(system_routes.router, prefix="/system", tags=["system"])
app.include_router(dashboard_routes.router, prefix="/dashboard", tags=["dashboard"])

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
