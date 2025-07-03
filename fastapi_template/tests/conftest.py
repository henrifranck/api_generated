import sys
from pathlib import Path

# Ajoute le répertoire parent au chemin Python
sys.path.append(str(Path(__file__).parent.parent))
from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from main import app
from app.db.base_class import Base
from app.db.session import SessionLocal
from app.db import session as db_session
from app.db import base
from app.api import deps

# Create an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 2. Patch global
db_session.SessionLocal = TestingSessionLocal

# Create tables
Base.metadata.create_all(bind=engine)


def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


# 5. Fixtures
@pytest.fixture
def db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def client(db):
    from main import app  # après le patch
    def override_get_db():
        try:
            yield db
        finally:
            db.close()
    app.dependency_overrides[deps.get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides = {}
