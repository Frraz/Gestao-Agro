import pytest
from src.main import create_app
from src.models.db import db
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

def fazenda_exemplo():
    return {
        "nome": "Fazenda Boa Vista",
        "matricula": "12345",
        "tamanho_total": 100.0,
        "area_consolidada": 40.0,
        "tamanho_disponivel": 60.0,
        "tipo_posse": TipoPosse.PROPRIA,
        "municipio": "Uberlândia",
        "estado": "MG",
        "recibo_car": "CAR-2025"
    }

def test_cria_fazenda(session):
    data = fazenda_exemplo()
    fazenda = Fazenda(**data)
    session.add(fazenda)
    session.commit()
    found = Fazenda.query.filter_by(matricula="12345").first()
    assert found is not None
    assert found.nome == "Fazenda Boa Vista"
    assert found.tamanho_total == 100.0
    assert found.area_consolidada == 40.0
    assert found.tamanho_disponivel == 60.0
    assert found.tipo_posse == TipoPosse.PROPRIA
    assert found.municipio == "Uberlândia"
    assert found.estado == "MG"
    assert found.recibo_car == "CAR-2025"

def test_atualiza_fazenda(session):
    data = fazenda_exemplo()
    fazenda = Fazenda(**data)
    session.add(fazenda)
    session.commit()
    fazenda.nome = "Fazenda Nova Vista"
    fazenda.area_consolidada = 50.0
    fazenda.atualizar_tamanho_disponivel()
    session.commit()
    found = Fazenda.query.filter_by(matricula="12345").first()
    assert found.nome == "Fazenda Nova Vista"
    assert found.area_consolidada == 50.0
    assert found.tamanho_disponivel == 50.0  # 100 - 50

def test_deleta_fazenda(session):
    data = fazenda_exemplo()
    fazenda = Fazenda(**data)
    session.add(fazenda)
    session.commit()
    session.delete(fazenda)
    session.commit()
    found = Fazenda.query.filter_by(matricula="12345").first()
    assert found is None

def test_repr(session):
    data = fazenda_exemplo()
    fazenda = Fazenda(**data)
    session.add(fazenda)
    session.commit()
    found = Fazenda.query.filter_by(matricula="12345").first()
    assert repr(found) == "<Fazenda Fazenda Boa Vista - 12345>"

def test_calcular_tamanho_disponivel(session):
    data = fazenda_exemplo()
    fazenda = Fazenda(**data)
    session.add(fazenda)
    session.commit()
    found = Fazenda.query.filter_by(matricula="12345").first()
    assert found.calcular_tamanho_disponivel == 60.0