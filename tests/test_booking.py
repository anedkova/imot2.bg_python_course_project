import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from datetime import datetime, date
from main import app
from database import get_db
from routers.auth import get_current_user
import models

client = TestClient(app)


def mock_agent():
    return models.User(id=1, username="agent_pro", role="agent", is_verified=True)


def mock_client():
    return models.User(id=2, username="buyer", role="client", is_verified=True)


@pytest.fixture(autouse=True)
def clean_overrides():
    yield
    app.dependency_overrides.clear()


def test_create_booking_success():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_client

    mock_db.query.return_value.filter.return_value.first.side_effect = [
        models.Property(id=10, title="Lux Apartment", owner_id=1),
        None
    ]

    def mock_add(obj):
        obj.id = 1
        obj.status = "pending"
        obj.booking_date = datetime(2026, 5, 20, 10, 0)

    mock_db.add.side_effect = mock_add

    payload = {"property_id": 10, "booking_date": "2026-05-20T10:00:00"}
    response = client.post("/bookings/", json=payload)

    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    assert response.json()["property_id"] == 10


def test_create_booking_slot_taken():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_client

    mock_db.query.return_value.filter.return_value.first.side_effect = [
        models.Property(id=10),
        models.Booking(id=1, status="confirmed")
    ]

    payload = {"property_id": 10, "booking_date": "2026-05-20T10:00:00"}
    response = client.post("/bookings/", json=payload)
    assert response.status_code == 400
    assert "already booked" in response.json()["detail"]


def test_get_calendar_as_agent():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_agent

    fake_booking = models.Booking(
        id=1, property_id=10, client_id=2,
        booking_date=datetime(2026, 5, 20, 10, 0), status="confirmed"
    )
    mock_db.query.return_value.join.return_value.filter.return_value.order_by.return_value.all.return_value = [
        fake_booking]

    response = client.get("/bookings/calendar?day=2026-05-20")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == 1


def test_update_booking_status_success():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_agent

    mock_prop = models.Property(id=10, owner_id=1)
    mock_booking = models.Booking(id=5, property_id=10, status="pending")
    mock_booking.property = mock_prop

    mock_db.query.return_value.join.return_value.filter.return_value.first.return_value = mock_booking

    response = client.patch("/bookings/5/status?new_status=confirmed")
    assert response.status_code == 200
    assert mock_booking.status == "confirmed"
    assert mock_db.commit.called


def test_update_booking_forbidden_not_owner():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_agent

    mock_prop = models.Property(id=10, owner_id=99)
    mock_booking = models.Booking(id=5, property_id=10)
    mock_booking.property = mock_prop

    mock_db.query.return_value.join.return_value.filter.return_value.first.return_value = mock_booking

    response = client.patch("/bookings/5/status?new_status=confirmed")
    assert response.status_code == 403
    assert "manage bookings for your own properties" in response.json()["detail"]