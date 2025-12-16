import pytest
import datetime


class TestHealthEndpoint:
    def test_health_check(self, client):
        """Тест эндпоинта /health"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data


class TestCreateRecord:
    def test_create_record_success(self, client, sample_record_data):
        """Успешное создание записи"""
        response = client.post("/records", json=sample_record_data)

        assert response.status_code == 201
        data = response.json()

        assert "id" in data
        assert data["title"] == sample_record_data["title"]
        assert data["details"] == sample_record_data["details"]
        assert data["is_done"] == sample_record_data["is_done"]
        assert data["record_date"] == sample_record_data["record_date"]
        assert "created_at" in data
        assert data["updated_at"] is None

    def test_create_record_invalid_title(self, client):
        """Создание записи с некорректным заголовком"""
        # Слишком короткий заголовок
        data = {"title": "a"}
        response = client.post("/records", json=data)

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_create_record_invalid_record_date(self, client):
        """Создание записи с некорректной датой"""
        data = {
            "title": "Test record",
            "record_date": "not-a-date"
        }
        response = client.post("/records", json=data)

        assert response.status_code == 422


class TestGetRecord:
    def test_get_existing_record(self, client, create_test_records):
        """Получение существующей записи"""
        record = create_test_records[0]

        response = client.get(f"/records/{record.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == record.id
        assert data["title"] == record.title

class TestUpdateRecord:
    def test_update_record_partial(self, client, create_test_records):
        """Частичное обновление записи"""
        record = create_test_records[0]

        update_data = {
            "is_done": True
        }

        response = client.put(f"/records/{record.id}", json=update_data)

        assert response.status_code == 200
        data = response.json()

        assert data["is_done"] is True
        assert data["title"] == record.title  # не изменилось
        assert data["updated_at"] is not None  # должно обновиться

    def test_update_record_full(self, client, create_test_records):
        """Полное обновление записи"""
        record = create_test_records[0]

        update_data = {
            "title": "Updated title",
            "details": "Updated details",
            "is_done": True,
            "record_date": (datetime.datetime.now() + datetime.timedelta(days=14)).isoformat()
        }

        response = client.put(f"/records/{record.id}", json=update_data)

        assert response.status_code == 200
        data = response.json()

        assert data["title"] == "Updated title"
        assert data["details"] == "Updated details"
        assert data["is_done"] is True

class TestDeleteRecord:
    def test_delete_record_success(self, client, create_test_records):
        """Успешное удаление записи"""
        record = create_test_records[0]

        # Удаляем запись
        response = client.delete(f"/records/{record.id}")
        assert response.status_code == 204

        # Проверяем, что запись удалена
        response = client.get(f"/records/{record.id}")
        assert response.status_code == 404