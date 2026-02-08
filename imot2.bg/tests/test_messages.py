import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from datetime import datetime
from main import app
from database import get_db
from routers.auth import get_current_user
import models

client = TestClient(app)


def mock_sender():
    return models.User(id=1, username="sender_user", email="sender@test.com")


def mock_receiver():
    return models.User(id=2, username="receiver_user", email="receiver@test.com")


@pytest.fixture(autouse=True)
def clean_overrides():
    yield
    app.dependency_overrides.clear()


def test_send_message_success():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_sender

    mock_db.query.return_value.filter.return_value.first.return_value = mock_receiver()

    def mock_add(obj):
        obj.id = 100
        obj.timestamp = datetime.now()

    mock_db.add.side_effect = mock_add

    payload = {"receiver_id": 2, "content": "Hello there!"}
    response = client.post("/messages/", json=payload)

    assert response.status_code == 200
    assert response.json()["content"] == "Hello there!"
    assert response.json()["sender_id"] == 1
    assert mock_db.commit.called


def test_send_message_receiver_not_found():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_sender

    mock_db.query.return_value.filter.return_value.first.return_value = None

    response = client.post("/messages/", json={"receiver_id": 999, "content": "Hi"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Receiver not found"


def test_send_message_to_self():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_sender  # ID = 1

    mock_db.query.return_value.filter.return_value.first.return_value = mock_sender()

    response = client.post("/messages/", json={"receiver_id": 1, "content": "Me to myself"})
    assert response.status_code == 400
    assert "cannot send messages to yourself" in response.json()["detail"]


def test_get_my_messages_inbox():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_sender

    fake_msgs = [
        models.Message(id=1, sender_id=1, receiver_id=2, content="Msg 1", timestamp=datetime.now()),
        models.Message(id=2, sender_id=2, receiver_id=1, content="Msg 2", timestamp=datetime.now())
    ]
    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = fake_msgs

    response = client.get("/messages/inbox")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_specific_conversation():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_sender

    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

    response = client.get("/messages/chat/2")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
