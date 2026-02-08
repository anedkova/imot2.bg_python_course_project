import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from main import app
from database import get_db
import models

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_overrides():
    yield
    app.dependency_overrides.clear()


@patch("routers.auth.pwd_context.hash")
def test_register_success(mock_hash):
    mock_hash.return_value = "fake_hashed_password"

    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    def mock_add_side_effect(user_obj):
        user_obj.id = 1
        return None

    mock_db.add.side_effect = mock_add_side_effect
    mock_db.query.return_value.filter.return_value.first.return_value = None

    payload = {
        "email": "new@test.com", "username": "tester", "password": "password123",
        "first_name": "Ivan", "last_name": "Ivanov", "role": "client"
    }
    response = client.post("/auth/register", json=payload)

    assert response.status_code == 200
    assert response.json()["id"] == 1
    assert mock_db.commit.called
    mock_hash.assert_called_once_with("password123")


@patch("routers.auth.pwd_context.hash")
def test_register_user_already_exists(mock_hash):
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    mock_db.query.return_value.filter.return_value.first.return_value = models.User(id=1)

    payload = {
        "email": "exists@test.com", "username": "exists", "password": "123",
        "first_name": "A", "last_name": "B", "role": "client"
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Email or Username already exists"


@patch("routers.auth.pwd_context.hash")
def test_register_invalid_role(mock_hash):
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    mock_db.query.return_value.filter.return_value.first.return_value = None

    payload = {
        "email": "role@test.com", "username": "user", "password": "123",
        "first_name": "A", "last_name": "B", "role": "admin"
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid role selection"


def test_login_success():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    with pytest.MonkeyPatch().context() as mp:
        from routers.auth import pwd_context
        mp.setattr(pwd_context, "verify", lambda p, h: True)

        fake_user = models.User(username="testuser", hashed_password="hashed")
        mock_db.query.return_value.filter.return_value.first.return_value = fake_user

        response = client.post("/auth/login", json={"username": "testuser", "password": "password"})

        assert response.status_code == 200
        assert response.cookies.get("username") == "testuser"
        assert response.json()["message"] == "Login successful"


def test_login_invalid_credentials():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    mock_db.query.return_value.filter.return_value.first.return_value = None

    response = client.post("/auth/login", json={"username": "wrong", "password": "password"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"


def test_logout():
    response = client.get("/auth/logout", follow_redirects=False)
    assert response.status_code == 303
    cookies = response.headers.get("set-cookie", "")
    assert 'username=""' in cookies or 'Max-Age=0' in cookies


def test_get_current_user_no_cookie():
    from routers.auth import get_current_user
    mock_request = MagicMock()
    mock_request.cookies = {}

    with pytest.raises(Exception) as exc:
        get_current_user(request=mock_request, db=MagicMock())
    assert "401" in str(exc.value)