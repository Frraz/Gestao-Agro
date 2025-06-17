import pytest
from src.main import create_app

@pytest.fixture
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    return app

@pytest.fixture
def client(app):
    return app.test_client()

def test_home_status(client):
    response = client.get("/")
    assert response.status_code in (200, 302)  # 302 se redireciona para login