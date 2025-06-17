import pytest
from datetime import date
from decimal import Decimal
from src.main import create_app
from src.models.db import db
from src.models.fazenda import Fazenda, TipoPosse
from src.models.endividamento import Endividamento, EndividamentoFazenda, Parcela

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
        nome="Fazenda Sol",
        matricula="FAZ-001",
        tamanho_total=100.0,
        area_consolidada=20.0,
        tamanho_disponivel=80.0,
        tipo_posse=TipoPosse.PROPRIA,
        municipio="Município X",
        estado="UF",
        recibo_car="CAR-TESTE"
    )

def endividamento_exemplo():
    return Endividamento(
        banco="Banco Teste",
        numero_proposta="PROP-DEL",
        data_emissao=date(2024, 1, 1),
        data_vencimento_final=date(2025, 1, 1),
        taxa_juros=Decimal("8.00"),
        tipo_taxa_juros="ano",
        prazo_carencia=6,
        valor_operacao=Decimal("200000.00")
    )

def test_endividamento_cascade_delete(session):
    fazenda = fazenda_exemplo()
    endiv = endividamento_exemplo()
    session.add_all([fazenda, endiv])
    session.commit()

    # Vincula uma fazenda
    vinculo = EndividamentoFazenda(
        endividamento=endiv,
        fazenda=fazenda,
        hectares=Decimal("50.0"),
        tipo="objeto_credito",
        descricao="Vínculo para teste"
    )
    # Cria duas parcelas
    parcela1 = Parcela(
        endividamento=endiv,
        data_vencimento=date(2024, 6, 1),
        valor=Decimal("10000.00"),
        pago=False
    )
    parcela2 = Parcela(
        endividamento=endiv,
        data_vencimento=date(2024, 12, 1),
        valor=Decimal("15000.00"),
        pago=False
    )
    session.add_all([vinculo, parcela1, parcela2])
    session.commit()

    # Verifica que ambos existem
    assert Endividamento.query.count() == 1
    assert EndividamentoFazenda.query.count() == 1
    assert Parcela.query.count() == 2

    # Deleta o endividamento
    session.delete(endiv)
    session.commit()

    # Todos os vínculos e parcelas devem ter sido deletados
    assert Endividamento.query.count() == 0
    assert EndividamentoFazenda.query.count() == 0
    assert Parcela.query.count() == 0