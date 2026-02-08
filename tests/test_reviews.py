import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from main import app
from database import get_db
from routers.auth import get_current_user
import models

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_overrides():
    yield
    app.dependency_overrides.clear()

def mock_reviewer():
    return models.User(id=1, username="reviewer_1", role="client")


def test_create_review_success():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_reviewer

    mock_db.query.return_value.filter.return_value.first.side_effect = [
        models.Property(id=10, title="Beach House"),
        None
    ]

    def mock_add(obj):
        obj.id = 50

    mock_db.add.side_effect = mock_add

    payload = {"property_id": 10, "rating": 5, "comment": "Amazing place!"}
    response = client.post("/reviews/", json=payload)

    assert response.status_code == 200
    assert response.json()["rating"] == 5
    assert response.json()["author_id"] == 1
    assert mock_db.commit.called


def test_create_review_duplicate_error():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_reviewer

    mock_db.query.return_value.filter.return_value.first.side_effect = [
        models.Property(id=10),
        models.Review(id=1, author_id=1, property_id=10)
    ]

    payload = {"property_id": 10, "rating": 4, "comment": "Another one"}
    response = client.post("/reviews/", json=payload)

    assert response.status_code == 400
    assert "already reviewed this property" in response.json()["detail"]


def test_create_review_invalid_rating():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_reviewer

    mock_db.query.return_value.filter.return_value.first.return_value = models.Property(id=10)

    payload = {"property_id": 10, "rating": 6, "comment": "Too high"}
    response = client.post("/reviews/", json=payload)

    assert response.status_code == 422

def test_create_review_property_not_found():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_reviewer

    mock_db.query.return_value.filter.return_value.first.return_value = None

    response = client.post("/reviews/", json={"property_id": 999, "rating": 5, "comment": "X"})
    assert response.status_code == 404
    assert "Property not found" in response.json()["detail"]


def test_get_property_reviews():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    fake_reviews = [
        models.Review(id=1, property_id=10, rating=5, comment="Great", author_id=1),
        models.Review(id=2, property_id=10, rating=4, comment="Good", author_id=2)
    ]
    mock_db.query.return_value.filter.return_value.all.return_value = fake_reviews

    response = client.get("/reviews/property/10")
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["author_id"] == 1
