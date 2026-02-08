import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from main import app
from database import get_db
from routers.auth import get_current_user
import models

client = TestClient(app)


def mock_admin_user():
    return models.User(
        id=1, email="admin@test.com", username="admin",
        first_name="Admin", last_name="User", role="admin", is_verified=True
    )


def mock_client_user():
    return models.User(
        id=2, email="client@test.com", username="tester",
        first_name="Ivan", last_name="Ivanov", role="client", is_verified=True
    )


@pytest.fixture(autouse=True)
def clean_overrides():
    yield
    app.dependency_overrides.clear()


@patch("routers.auth.pwd_context.hash")
def test_register_success(mock_pwd_hash):
    mock_pwd_hash.return_value = "fake_hashed_password"

    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    mock_db.query.return_value.filter.return_value.first.return_value = None

    def mock_add_side_effect(obj):
        obj.id = 99

    mock_db.add.side_effect = mock_add_side_effect

    payload = {
        "email": "new@test.com", "username": "newuser", "password": "password123",
        "first_name": "Test", "last_name": "User", "role": "client"
    }
    response = client.post("/auth/register", json=payload)

    assert response.status_code == 200
    assert response.json()["username"] == "newuser"
    assert mock_pwd_hash.called

def test_login_success():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    with pytest.MonkeyPatch().context() as mp:
        from routers.auth import pwd_context
        mp.setattr(pwd_context, "verify", lambda p, h: True)

        fake_user = models.User(username="tester", hashed_password="hashed", id=2)
        mock_db.query.return_value.filter.return_value.first.return_value = fake_user

        response = client.post("/auth/login", json={"username": "tester", "password": "password"})
        assert response.status_code == 200
        assert response.cookies.get("username") == "tester"


def test_logout():
    response = client.get("/auth/logout", follow_redirects=False)
    assert response.status_code == 303
    assert 'username=""' in response.headers.get("set-cookie", "")


def test_get_admin_stats():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_admin_user

    mock_db.query.return_value.count.return_value = 10
    mock_db.query.return_value.filter.return_value.count.return_value = 3

    response = client.get("/admin/stats")
    assert response.status_code == 200
    assert response.json()["user_stats"]["total_users"] == 10


def test_verify_user_success():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_admin_user

    target_user = models.User(
        id=10, email="agent@test.com", username="agent",
        first_name="A", last_name="B", role="agent", is_verified=False
    )
    mock_db.query.return_value.filter.return_value.first.return_value = target_user

    response = client.patch("/admin/verify/10")
    assert response.status_code == 200
    assert response.json()["is_verified"] is True


def test_get_all_reviews_admin():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_admin_user

    fake_review = models.Review(id=1, property_id=5, author_id=2, rating=5, comment="Ok")
    mock_db.query.return_value.all.return_value = [fake_review]

    response = client.get("/admin/reviews")
    assert response.status_code == 200
    assert response.json()[0]["comment"] == "Ok"


def test_admin_access_denied_for_client():
    app.dependency_overrides[get_current_user] = mock_client_user
    response = client.get("/admin/stats")
    assert response.status_code == 403


def test_admin_verify_user_not_found():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: models.User(id=1, role="admin")

    mock_db.query.return_value.filter.return_value.first.return_value = None

    response = client.patch("/admin/verify/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Target user not found"


def test_admin_delete_review_not_found():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: models.User(role="admin")

    mock_db.query.return_value.filter.return_value.first.return_value = None

    response = client.delete("/admin/reviews/888")
    assert response.status_code == 404
    assert response.json()["detail"] == "Review not found"


def test_admin_get_all_bookings_success():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: models.User(role="admin")

    mock_db.query.return_value.all.return_value = []

    response = client.get("/admin/bookings")
    assert response.status_code == 200
    assert isinstance(response.json(), list)