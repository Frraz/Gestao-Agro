# /tests/conftest.py

import pytest
from src.main import create_app
from src.models.db import db

@pytest.fixture
def app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        # Opcional: desabilite o cache real durante testes
        "REDIS_URL": "redis://localhost:6379/15",
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def pessoa_obj(app):
    from src.models.pessoa import Pessoa
    obj = Pessoa(nome="Pessoa Teste", cpf_cnpj="12345678900")
    db.session.add(obj)
    db.session.commit()
    return obj

# Fixture opcional para garantir que nenhum teste use Redis real
import pytest
from unittest.mock import MagicMock

@pytest.fixture(autouse=True)
def mock_cache(monkeypatch):
    monkeypatch.setattr("src.utils.cache.cache", MagicMock())