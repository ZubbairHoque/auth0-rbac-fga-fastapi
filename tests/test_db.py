import pytest
import pytest_asyncio
from app.database import engine, get_db
from app.database import Base
from app.database import ResourceDB

@pytest_asyncio.fixture(loop_scope="session", autouse=True)
async def db_engine_fixture():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture()
async def db_session():
    session_generator = get_db()
    session = await anext(session_generator)
    for tbl in reversed(Base.metadata.sorted_tables):
        await session.execute(tbl.delete())
    await session.commit()
    yield session
    await session.close()

@pytest.mark.asyncio
async def test_get_db_yields_session():
    """Test that get_db yields an AsyncSession."""
    from sqlalchemy.ext.asyncio import AsyncSession
    
    session_generator = get_db()
    session = await anext(session_generator)
    
    assert isinstance(session, AsyncSession)
    assert session.is_active
    
    await session.close()

@pytest.mark.asyncio
async def test_resource_db_model(db_session):
    """Test that we can create and retrieve a ResourceDB instance."""
    from app.database import ResourceDB
    from sqlalchemy import select
    import uuid
    
    # Create
    resource_id = str(uuid.uuid4())
    new_resource = ResourceDB(
        id=resource_id,
        name="Test Resource",
        description="A test resource",
        resource_type="api"
    )
    db_session.add(new_resource)
    await db_session.commit()
    
    # Retrieve
    result = await db_session.execute(select(ResourceDB).where(ResourceDB.id == resource_id))
    retrieved_resource = result.scalar_one_or_none()
    
    assert retrieved_resource is not None
    assert retrieved_resource.id == resource_id
    assert retrieved_resource.name == "Test Resource"
    assert retrieved_resource.description == "A test resource"
    assert retrieved_resource.resource_type == "api"

@pytest.mark.asyncio
async def test_database_initialization(db_engine_fixture):
    """Test that the database can be initialized and tables created."""
    from sqlalchemy import inspect
    from app.database import engine
    
    def run_inspections(conn):
        inspector = inspect(conn)
        
        # Check that the resources table exists
        assert "resources" in inspector.get_table_names()
        
        # Check columns
        columns = [col["name"] for col in inspector.get_columns("resources")]
        assert "id" in columns
        assert "name" in columns
        assert "description" in columns
        assert "resource_type" in columns
        assert "created_at" in columns

    # init_db is called by the db_engine_fixture, so we just need to check tables exist
    async with engine.connect() as conn:
        await conn.run_sync(run_inspections)

@pytest.mark.asyncio
async def test_session_management(db_session):
    """Test that the session is properly managed (created, used, closed)."""
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select
    
    # Session is already created and provided by db_session fixture
    # Check it's an async session
    assert isinstance(db_session, AsyncSession)
    
    # Check it's active
    assert db_session.is_active
    
    # Perform a simple query to verify
    result = await db_session.execute(select(ResourceDB))
    assert result is not None
    
    # Session should be closed after the test (handled by fixture's finally block)
    # We can't easily check it's closed from here, but the fixture teardown does this.
