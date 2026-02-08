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


@patch("main.templates.TemplateResponse")
def test_home_page_logged_in(mock_template):
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    fake_user = models.User(id=1, username="ivan_test", email="ivan@test.com")
    mock_db.query.return_value.filter.return_value.first.return_value = fake_user

    client.cookies.set("username", "ivan_test")

    response = client.get("/")

    assert response.status_code == 200
    assert mock_template.called
    assert mock_template.call_args[0][1] == "index.html"


def test_property_details_not_found():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    mock_db.query.return_value.filter.return_value.first.return_value = None

    response = client.get("/properties/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Property not found"
