import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from main import app
from database import get_db, SessionLocal
from routers.auth import get_current_user
import models
import io

def mock_verified_agent():
    return models.User(id=1, username="agent1", role="agent", is_verified=True)


def mock_unverified_agent():
    return models.User(id=2, username="agent2", role="agent", is_verified=False)


def mock_admin():
    return models.User(id=3, username="admin", role="admin", is_verified=True)


@pytest.fixture(autouse=True)
def clean_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_get_properties_filters(client):
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    fake_prop = models.Property(
        id=1,
        title="Apartment",
        price=100.0,
        location="Sofia",
        owner_id=1,
        property_type="rent",  # Липсваше
        status="available"  # Липсваше
    )

    mock_query = mock_db.query.return_value.join.return_value.filter.return_value
    mock_query.filter.return_value.filter.return_value.filter.return_value.all.return_value = [fake_prop]

    response = client.get("/properties/?title=Apartment&prop_type=rent&location=Sofia")

    assert response.status_code == 200
    assert response.json()[0]["status"] == "available"


def test_create_property_success(client):
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_verified_agent

    def mock_add_side_effect(obj):
        obj.id = 1
        obj.status = "available"
        return None

    mock_db.add.side_effect = mock_add_side_effect

    payload = {
        "title": "New House",
        "description": "Big house",
        "price": 500000,
        "property_type": "sale",
        "location": "Plovdiv"
    }

    response = client.post("/properties/", json=payload)

    assert response.status_code == 200
    assert response.json()["status"] == "available"


def test_create_property_unverified_error(client):
    app.dependency_overrides[get_current_user] = mock_unverified_agent
    payload = {"title": "T", "description": "D", "price": 10.0, "property_type": "sale", "location": "L"}
    response = client.post("/properties/", json=payload)
    assert response.status_code == 403
    assert "Account not verified" in response.json()["detail"]


def test_upload_image_success(client):
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_verified_agent

    mock_prop = models.Property(id=1, owner_id=1)
    mock_db.query.return_value.filter.return_value.first.return_value = mock_prop

    file_content = b"fake-image-binary"
    file = io.BytesIO(file_content)

    response = client.post(
        "/properties/1/upload-image",
        files={"file": ("test.jpg", file, "image/jpeg")}
    )

    assert response.status_code == 200
    assert "url" in response.json()
    assert mock_db.add.called


def test_upload_image_forbidden_not_owner(client):
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_verified_agent

    mock_prop = models.Property(id=1, owner_id=99)
    mock_db.query.return_value.filter.return_value.first.return_value = mock_prop

    response = client.post("/properties/1/upload-image", files={"file": ("t.jpg", b"abc")})
    assert response.status_code == 403


@patch("os.path.exists")
@patch("os.remove")
def test_delete_property_as_admin(mock_remove, mock_exists, client):
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_admin

    mock_exists.return_value = True
    mock_img = models.PropertyImage(url="/static/uploads/img.jpg")
    mock_prop = models.Property(id=1, owner_id=5, images=[mock_img])
    mock_db.query.return_value.filter.return_value.first.return_value = mock_prop

    response = client.delete("/properties/1")
    assert response.status_code == 204
    assert mock_remove.called
    assert mock_db.delete.called


def test_delete_property_not_found(client):
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_verified_agent
    mock_db.query.return_value.filter.return_value.first.return_value = None

    response = client.delete("/properties/999")
    assert response.status_code == 404


def test_get_property_api_details(client, db_session):
    prop = models.Property(title="API House", price=1000, location="Sofia", property_type="sale", owner_id=1)
    db_session.add(prop)
    db_session.commit()

    response = client.get(f"/properties/{prop.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "API House"
    assert "price" in data
