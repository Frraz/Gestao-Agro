import pytest
import datetime
from src.main import create_app
from src.models.db import db
from src.models.pessoa import Pessoa
from src.models.fazenda import Fazenda, TipoPosse
from src.models.documento import Documento, TipoDocumento, TipoEntidade

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

def documento_para_pessoa(pessoa):
    return Documento(
        nome="Documento Pessoa",
        tipo=TipoDocumento.CERTIDOES,
        tipo_personalizado=None,
        data_emissao=datetime.date(2024,1,1),
        data_vencimento=datetime.date(2025,1,1),
        tipo_entidade=TipoEntidade.PESSOA,
        pessoa=pessoa
    )

def documento_para_fazenda(fazenda):
    return Documento(
        nome="Documento Fazenda",
        tipo=TipoDocumento.CONTRATOS,
        tipo_personalizado=None,
        data_emissao=datetime.date(2024,1,1),
        data_vencimento=datetime.date(2025,1,1),
        tipo_entidade=TipoEntidade.FAZENDA,
        fazenda=fazenda
    )

def test_documento_associado_a_pessoa(session):
    pessoa = pessoa_exemplo()
    doc = documento_para_pessoa(pessoa)
    session.add(pessoa)
    session.add(doc)
    session.commit()
    pessoa_db = Pessoa.query.filter_by(cpf_cnpj="12345678901").first()
    assert len(pessoa_db.documentos) == 1
    assert pessoa_db.documentos[0].nome == "Documento Pessoa"
    doc_db = Documento.query.filter_by(nome="Documento Pessoa").first()
    assert doc_db.pessoa.nome == "Maria Teste"
    assert doc_db.fazenda is None

def test_documento_associado_a_fazenda(session):
    fazenda = fazenda_exemplo()
    doc = documento_para_fazenda(fazenda)
    session.add(fazenda)
    session.add(doc)
    session.commit()
    fazenda_db = Fazenda.query.filter_by(matricula="FZ-001").first()
    assert len(fazenda_db.documentos) == 1
    assert fazenda_db.documentos[0].nome == "Documento Fazenda"
    doc_db = Documento.query.filter_by(nome="Documento Fazenda").first()
    assert doc_db.fazenda.nome == "Fazenda Relacionada"
    assert doc_db.pessoa is None
