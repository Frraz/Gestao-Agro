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


def test_pessoa_fazenda_sem_datas(session):
    """Test que verifica que o modelo PessoaFazenda não armazena datas"""
    pessoa = pessoa_exemplo()
    fazenda = fazenda_exemplo()
    
    session.add(pessoa)
    session.add(fazenda)
    session.commit()
    
    # Create the relationship through the intermediate model
    vinculo = PessoaFazenda(
        pessoa_id=pessoa.id,
        fazenda_id=fazenda.id,
        tipo_posse=TipoPosse.PROPRIA
    )
    session.add(vinculo)
    session.commit()

    # Verify that the relationship was created correctly
    vinculo_db = PessoaFazenda.query.filter_by(pessoa_id=pessoa.id, fazenda_id=fazenda.id).first()
    assert vinculo_db is not None
    assert vinculo_db.tipo_posse == TipoPosse.PROPRIA
    # Verify that no date fields exist (this test should pass after our changes)
    assert not hasattr(vinculo_db, 'data_inicio')
    assert not hasattr(vinculo_db, 'data_fim')


def test_multiplas_associacoes_mesmo_tipo(session):
    """Test que verifica que a mesma pessoa pode ter múltiplas associações com a mesma fazenda do mesmo tipo"""
    pessoa = pessoa_exemplo()
    fazenda = fazenda_exemplo()
    
    session.add(pessoa)
    session.add(fazenda)
    session.commit()
    
    # Create multiple relationships with the same tipo_posse
    # This should be allowed since we're not tracking dates anymore
    vinculo1 = PessoaFazenda(
        pessoa_id=pessoa.id,
        fazenda_id=fazenda.id,
        tipo_posse=TipoPosse.PROPRIA
    )
    vinculo2 = PessoaFazenda(
        pessoa_id=pessoa.id,
        fazenda_id=fazenda.id,
        tipo_posse=TipoPosse.PROPRIA
    )
    
    session.add(vinculo1)
    session.add(vinculo2)
    session.commit()
    
    # Verify that multiple relationships were created
    vinculos = PessoaFazenda.query.filter_by(pessoa_id=pessoa.id, fazenda_id=fazenda.id).all()
    assert len(vinculos) == 2


def test_diferentes_tipos_vinculo(session):
    """Test que verifica que a mesma pessoa pode ter diferentes tipos de vínculo com a mesma fazenda"""
    pessoa = pessoa_exemplo()
    fazenda = fazenda_exemplo()
    
    session.add(pessoa)
    session.add(fazenda)
    session.commit()
    
    # Create relationships with different tipos_posse
    vinculo1 = PessoaFazenda(
        pessoa_id=pessoa.id,
        fazenda_id=fazenda.id,
        tipo_posse=TipoPosse.PROPRIA
    )
    vinculo2 = PessoaFazenda(
        pessoa_id=pessoa.id,
        fazenda_id=fazenda.id,
        tipo_posse=TipoPosse.ARRENDADA
    )
    
    session.add(vinculo1)
    session.add(vinculo2)
    session.commit()
    
    # Verify that both relationships were created
    vinculos = PessoaFazenda.query.filter_by(pessoa_id=pessoa.id, fazenda_id=fazenda.id).all()
    assert len(vinculos) == 2
    
    tipos_found = {v.tipo_posse for v in vinculos}
    assert TipoPosse.PROPRIA in tipos_found
    assert TipoPosse.ARRENDADA in tipos_found


def test_contagem_fazendas_pessoa(session):
    """Test que verifica que a contagem de fazendas por pessoa funciona corretamente"""
    pessoa = pessoa_exemplo()
    fazenda1 = fazenda_exemplo()
    fazenda2 = Fazenda(
        nome="Fazenda Teste 2",
        matricula="FZ-002",
        tamanho_total=200.0,
        area_consolidada=50.0,
        tamanho_disponivel=150.0,
        municipio="Testópolis",
        estado="TS"
    )
    
    session.add(pessoa)
    session.add(fazenda1)
    session.add(fazenda2)
    session.commit()
    
    # Associate pessoa with both fazendas
    vinculo1 = PessoaFazenda(
        pessoa_id=pessoa.id,
        fazenda_id=fazenda1.id,
        tipo_posse=TipoPosse.PROPRIA
    )
    vinculo2 = PessoaFazenda(
        pessoa_id=pessoa.id,
        fazenda_id=fazenda2.id,
        tipo_posse=TipoPosse.ARRENDADA
    )
    
    session.add(vinculo1)
    session.add(vinculo2)
    session.commit()
    
    # Verify the count
    pessoa_db = Pessoa.query.filter_by(cpf_cnpj="12345678901").first()
    assert pessoa_db.total_fazendas == 2