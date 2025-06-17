import pytest
from src.main import create_app
from src.models.db import db
from src.models.pessoa import Pessoa
from src.models.fazenda import Fazenda, TipoPosse

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

def pessoa_exemplo():
    return Pessoa(
        nome="Maria Teste",
        cpf_cnpj="12345678901",
        email="maria@teste.com"
    )

def fazenda_exemplo():
    return Fazenda(
        nome="Fazenda Relacionada",
        matricula="FZ-001",
        tamanho_total=100.0,
        area_consolidada=20.0,
        tamanho_disponivel=80.0,
        tipo_posse=TipoPosse.PROPRIA,
        municipio="Testópolis",
        estado="TS",
        recibo_car="CAR-TESTE"
    )

def test_relacionamento_pessoa_fazenda(session):
    pessoa = pessoa_exemplo()
    fazenda = fazenda_exemplo()
    # Associa a fazenda à pessoa
    pessoa.fazendas.append(fazenda)
    session.add(pessoa)
    session.commit()

    # Consulta do banco para garantir persistência
    pessoa_db = Pessoa.query.filter_by(cpf_cnpj="12345678901").first()
    fazenda_db = Fazenda.query.filter_by(matricula="FZ-001").first()
    
    # Pessoa reconhece a fazenda
    assert len(pessoa_db.fazendas) == 1
    assert pessoa_db.fazendas[0].nome == "Fazenda Relacionada"
    # Fazenda reconhece a pessoa
    assert len(fazenda_db.pessoas) == 1
    assert fazenda_db.pessoas[0].nome == "Maria Teste"