import pytest
import datetime
from decimal import Decimal
from src.main import create_app
from src.models.db import db
from src.models.pessoa import Pessoa
from src.models.fazenda import Fazenda, TipoPosse
from src.models.documento import Documento, TipoDocumento, TipoEntidade
from src.models.endividamento import Endividamento

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
    return Fazenda(
        nome="Fazenda Teste",
        matricula="FAZ-001",
        tamanho_total=100.0,
        area_consolidada=20.0,
        tamanho_disponivel=80.0,
        tipo_posse=TipoPosse.PROPRIA,
        municipio="Município X",
        estado="UF",
        recibo_car="CAR-TESTE"
    )

def pessoa_exemplo():
    return Pessoa(
        nome="Pessoa Teste",
        cpf_cnpj="00000000000",
        email="pessoa@teste.com"
    )

def test_documento_propriedades(session):
    fazenda = fazenda_exemplo()
    pessoa = pessoa_exemplo()
    session.add_all([fazenda, pessoa])
    session.commit()

    hoje = datetime.date.today()

    # Documento ainda NÃO vencido (vence hoje)
    doc = Documento(
        nome="Doc Válido",
        tipo=TipoDocumento.CERTIDOES,
        tipo_personalizado=None,
        data_emissao=hoje - datetime.timedelta(days=10),
        data_vencimento=hoje,
        tipo_entidade=TipoEntidade.FAZENDA,
        fazenda=fazenda
    )
    session.add(doc)
    session.commit()

    # Testa esta_vencido (não está vencido)
    assert doc.esta_vencido is False
    assert doc.proximo_vencimento == 0

    # Sem prazos de notificação, não notifica
    assert doc.precisa_notificar is False

    # Com prazos: 0 está nos prazos, portanto notifica
    doc.prazos_notificacao = [-1, 0, 5]
    assert doc.precisa_notificar is True

    # Agora torna o documento vencido (vencido ontem)
    doc.data_vencimento = hoje - datetime.timedelta(days=1)
    session.commit()
    doc.prazos_notificacao = [-1, 0, 5]
    # Mesmo -1 estando nos prazos, documento já está vencido, não notifica
    assert doc.precisa_notificar is False

    # Testa emails_notificacao setter/getter com lista
    doc.emails_notificacao = ["a@a.com", "b@b.com"]
    assert doc.emails_notificacao == ["a@a.com", "b@b.com"]

    # Testa emails_notificacao setter com string separada por vírgula
    doc.emails_notificacao = "c@c.com, d@d.com"
    assert doc.emails_notificacao == ["c@c.com", "d@d.com"]

    # Testa nome_entidade
    doc.data_vencimento = hoje  # volta para não vencido
    doc.tipo_entidade = TipoEntidade.FAZENDA
    doc.fazenda = fazenda
    doc.pessoa = None
    session.commit()
    assert doc.nome_entidade == "Fazenda Teste"

    # Troca para pessoa
    doc.tipo_entidade = TipoEntidade.PESSOA
    doc.fazenda = None
    doc.pessoa = pessoa
    session.commit()
    assert doc.nome_entidade == "Pessoa Teste"

def test_endividamento_to_dict(session):
    endiv = Endividamento(
        banco="Banco Teste",
        numero_proposta="PROP-TO-DICT",
        data_emissao=datetime.date(2024, 1, 1),
        data_vencimento_final=datetime.date(2025, 1, 1),
        taxa_juros=Decimal("7.5"),
        tipo_taxa_juros="ano",
        prazo_carencia=12,
        valor_operacao=Decimal("250000.00")
    )
    session.add(endiv)
    session.commit()

    d = endiv.to_dict()
    assert d["banco"] == "Banco Teste"
    assert d["numero_proposta"] == "PROP-TO-DICT"
    assert d["taxa_juros"] == 7.5
    assert d["valor_operacao"] == 250000.00
    assert d["tipo_taxa_juros"] == "ano"
    assert d["prazo_carencia"] == 12
    assert isinstance(d["created_at"], str)
    assert isinstance(d["updated_at"], str)