import pytest
from src.main import create_app
from src.models.db import db

@pytest.fixture
def app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"
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