import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import datetime

from app.app_main import app
from app.database import get_db
from app.models import Base, Record

# Создаем тестовую базу данных в памяти
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Фикстура для тестовой базы данных"""
    # Создаем таблицы
    Base.metadata.create_all(bind=engine)

    # Создаем сессию
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

    # Очищаем таблицы после теста
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """Фикстура для тестового клиента"""

    def override_get_db():
        try:
            yield db
        finally:
            pass

    # Подменяем зависимость базы данных
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    # Очищаем подмену
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


@pytest.fixture
def create_test_records(db):
    """Фикстура для создания тестовых записей"""
    records = []

    # Запись 1
    record1 = Record(
        title="Integrate medicine system with some analyzers",
        details="Medicine system v1.1; 10 analyzers Jerk Portable f1j12",
        is_done=False,
        record_date=datetime.datetime.now() + datetime.timedelta(days=1)
    )
    db.add(record1)
    records.append(record1)

    # Запись 2
    record2 = Record(
        title="Cut the Mr. D's hair",
        details="Mr. D want a cool haircut: 10$",
        is_done=True,
        record_date=datetime.datetime.now() + datetime.timedelta(days=3)
    )
    db.add(record2)
    records.append(record2)

    # Запись 3
    record3 = Record(
        title="Doctor's appointment",
        details="Check the prostate",
        is_done=False,
        record_date=datetime.datetime.now() + datetime.timedelta(days=7)
    )
    db.add(record3)
    records.append(record3)

    db.commit()

    for record in records:
        db.refresh(record)

    return records