import pytest
from src.main import create_app
from src.models.db import db
from src.models.pessoa import Pessoa
from src.models.fazenda import Fazenda
from src.models.pessoa_fazenda import PessoaFazenda, TipoPosse

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
        municipio="Testópolis",
        estado="TS",
        recibo_car="CAR-TESTE"
    )

def test_relacionamento_pessoa_fazenda(session):
    pessoa = pessoa_exemplo()
    fazenda = fazenda_exemplo()
    
    # Add to session first
    session.add(pessoa)
    session.add(fazenda)
    session.flush()  # To get the IDs
    
    # Create the relationship through PessoaFazenda
    vinculo = PessoaFazenda(
        pessoa_id=pessoa.id,
        fazenda_id=fazenda.id,
        tipo_posse=TipoPosse.PROPRIA
    )
    
    session.add(vinculo)
    session.commit()

    # Consulta do banco para garantir persistência
    pessoa_db = Pessoa.query.filter_by(cpf_cnpj="12345678901").first()
    fazenda_db = Fazenda.query.filter_by(matricula="FZ-001").first()
    
    # Pessoa reconhece a fazenda através do relacionamento
    assert len(pessoa_db.fazendas_associadas) == 1
    assert pessoa_db.fazendas_associadas[0].fazenda.nome == "Fazenda Relacionada"
    assert pessoa_db.fazendas_associadas[0].tipo_posse == TipoPosse.PROPRIA
    
    # Fazenda reconhece a pessoa através do relacionamento
    assert len(fazenda_db.pessoas_associadas) == 1
    assert fazenda_db.pessoas_associadas[0].pessoa.nome == "Maria Teste"
    assert fazenda_db.pessoas_associadas[0].tipo_posse == TipoPosse.PROPRIA