import pytest
from src.main import create_app
from src.models.db import db
from src.models.pessoa import Pessoa

@pytest.fixture
def app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test"
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def session(app):
    with app.app_context():
        yield db.session

def test_cria_pessoa(session):
    pessoa = Pessoa(
        nome="João da Silva",
        cpf_cnpj="11144477735",
        email="joao@email.com",
        telefone="34999999999",
        endereco="Rua X, 123"
    )
    session.add(pessoa)
    session.commit()
    found = Pessoa.query.filter_by(cpf_cnpj="11144477735").first()
    assert found is not None
    assert found.nome == "João da Silva"
    assert found.cpf_cnpj == "11144477735"
    assert found.email == "joao@email.com"
    assert found.telefone == "34999999999"
    assert found.endereco == "Rua X, 123"

def test_repr(session):
    pessoa = Pessoa(nome="Maria", cpf_cnpj="12345678901")
    session.add(pessoa)
    session.commit()
    found = Pessoa.query.filter_by(cpf_cnpj="12345678901").first()
    assert repr(found) == "<Pessoa Maria - 12345678901>"