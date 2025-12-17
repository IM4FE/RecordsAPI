import pytest
import asyncio
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool
import datetime

from app.app_main import app
from app.database import get_db
from app.models import Base, Record

# Создаем тестовую базу данных в памяти
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
def test_engine():
    engine = create_async_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    yield engine
    asyncio.run(engine.dispose())

TestingSessionLocal = async_sessionmaker(class_=AsyncSession)

@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine):
    """Фикстура БД + клиент"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal(bind=test_engine) as session:
        yield session
        await session.rollback()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture(scope="function")
def client(db_session):
    """Синхронный клиент"""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def sample_record_data():
    """Фикстура с примером данных записи"""
    return {
        "title": "Test Record",
        "details": "This is a test record",
        "is_done": False,
        "record_date": (datetime.datetime.now() + datetime.timedelta(days=7)).isoformat()
    }


@pytest_asyncio.fixture(scope="function")
async def create_test_records(db_session):
    """Фикстура для создания тестовых записей"""
    records = []

    # Запись 1
    record1 = Record(
        title="Integrate medicine system with some analyzers",
        details="Medicine system v1.1; 10 analyzers Jerk Portable f1j12",
        is_done=False,
        record_date=datetime.datetime.now() + datetime.timedelta(days=1)
    )
    db_session.add(record1)
    records.append(record1)

    # Запись 2
    record2 = Record(
        title="Cut the Mr. D's hair",
        details="Mr. D want a cool haircut: 10$",
        is_done=True,
        record_date=datetime.datetime.now() + datetime.timedelta(days=3)
    )
    db_session.add(record2)
    records.append(record2)

    # Запись 3
    record3 = Record(
        title="Doctor's appointment",
        details="Check the prostate",
        is_done=False,
        record_date=datetime.datetime.now() + datetime.timedelta(days=7)
    )
    db_session.add(record3)
    records.append(record3)

    await db_session.commit()

    for record in records:
        await db_session.refresh(record)

    return records