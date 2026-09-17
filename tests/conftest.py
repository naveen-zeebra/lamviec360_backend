import sys
from pathlib import Path

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.seed.seed_data import seed_database


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Initializes and seeds database before running any tests."""
    seed_database()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
