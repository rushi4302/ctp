import io
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.roles import UserRole
from app.core.security import create_access_token, hash_password
from app.database.base import Base
from app.dependencies.database import get_db
from app.main import app
from app.models.user import User

# Test database: In-memory SQLite isolated from PostgreSQL
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def citizen_user(db) -> User:
    user = User(
        email="citizen@test.civic.org",
        full_name="Citizen User",
        hashed_password=hash_password("Password123!"),
        role=UserRole.CITIZEN,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_user(db) -> User:
    user = User(
        email="admin@test.civic.org",
        full_name="Admin User",
        hashed_password=hash_password("Password123!"),
        role=UserRole.ADMIN,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def municipality_user(db) -> User:
    user = User(
        email="muni@test.civic.org",
        full_name="Municipality Officer",
        hashed_password=hash_password("Password123!"),
        role=UserRole.MUNICIPALITY,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user



@pytest.fixture
def field_worker_user(db) -> User:
    user = User(
        email="worker@test.civic.org",
        full_name="Field Worker 1",
        hashed_password=hash_password("Password123!"),
        role=UserRole.FIELD_WORKER,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def citizen_headers(citizen_user) -> dict:
    token = create_access_token({"sub": str(citizen_user.id), "role": citizen_user.role.value})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(admin_user) -> dict:
    token = create_access_token({"sub": str(admin_user.id), "role": admin_user.role.value})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def municipality_headers(municipality_user) -> dict:
    token = create_access_token({"sub": str(municipality_user.id), "role": municipality_user.role.value})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def field_worker_headers(field_worker_user) -> dict:
    token = create_access_token({"sub": str(field_worker_user.id), "role": field_worker_user.role.value})
    return {"Authorization": f"Bearer {token}"}



@pytest.fixture
def sample_image_bytes() -> bytes:
    img = Image.new("RGB", (100, 100), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()
