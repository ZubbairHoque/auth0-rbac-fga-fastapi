import asyncio
import sys
import selectors
import pytest

# Senior Fix: Force the SelectorEventLoop for the entire process on Windows.
# This must happen before any event loops are created.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"