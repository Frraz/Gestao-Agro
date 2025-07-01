import pytest
from datetime import date
from decimal import Decimal
from src.main import create_app
from src.models.db import db
from src.models.fazenda import Fazenda, TipoPosse
from src.models.endividamento import Endividamento, EndividamentoFazenda

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

def fazenda_exemplo(nome, matricula):
    return Fazenda(
        nome=nome,
        matricula=matricula,
        tamanho_total=100.0,
        area_consolidada=20.0,
        tamanho_disponivel=80.0,
        tipo_posse=TipoPosse.PROPRIA,
        municipio="Município X",
        estado="UF",
        recibo_car="CAR-TESTE"
    )

def endividamento_exemplo(numero_proposta="PROP-1"):
    return Endividamento(
        banco="Banco Teste",
        numero_proposta=numero_proposta,
        data_emissao=date(2024, 1, 1),
        data_vencimento_final=date(2025, 1, 1),
        taxa_juros=Decimal("12.34"),
        tipo_taxa_juros="ano",
        prazo_carencia=12,
        valor_operacao=Decimal("500000.00")
    )

def test_fazenda_area_calculation_properties(session):
    """Testa as novas propriedades de cálculo de área na fazenda."""
    fazenda = fazenda_exemplo("Fazenda Teste", "FAZ-001")
    endiv = endividamento_exemplo("PROP-123")

    session.add_all([fazenda, endiv])
    session.commit()

    # Inicialmente, nenhuma área usada em crédito
    assert fazenda.area_usada_credito == 0.0
    assert fazenda.area_disponivel_credito == 80.0
    assert fazenda.total_endividamentos == 0

    # Adicionar vínculo de crédito
    vinculo_credito = EndividamentoFazenda(
        endividamento=endiv,
        fazenda=fazenda,
        hectares=Decimal("30.0"),
        tipo="objeto_credito",
        descricao="Financiamento plantio"
    )
    
    session.add(vinculo_credito)
    session.commit()

    # Após adicionar vínculo de crédito
    assert fazenda.area_usada_credito == 30.0
    assert fazenda.area_disponivel_credito == 50.0  # 80 - 30
    assert fazenda.total_endividamentos == 1

    # Adicionar vínculo de garantia (não deve afetar área de crédito)
    vinculo_garantia = EndividamentoFazenda(
        endividamento=endiv,
        fazenda=fazenda,
        hectares=Decimal("25.0"),
        tipo="garantia",
        descricao="Garantia hipotecária"
    )
    
    session.add(vinculo_garantia)
    session.commit()

    # Garantias não afetam cálculo de área de crédito
    assert fazenda.area_usada_credito == 30.0
    assert fazenda.area_disponivel_credito == 50.0
    assert fazenda.total_endividamentos == 2

def test_fazenda_over_commitment(session):
    """Testa cenário onde área comprometida excede disponível."""
    fazenda = fazenda_exemplo("Fazenda Teste", "FAZ-002")
    endiv = endividamento_exemplo("PROP-456")

    session.add_all([fazenda, endiv])
    session.commit()

    # Comprometer mais área do que disponível
    vinculo = EndividamentoFazenda(
        endividamento=endiv,
        fazenda=fazenda,
        hectares=Decimal("90.0"),  # Mais que os 80 disponíveis
        tipo="objeto_credito",
        descricao="Financiamento grande"
    )
    
    session.add(vinculo)
    session.commit()

    assert fazenda.area_usada_credito == 90.0
    assert fazenda.area_disponivel_credito == -10.0  # Área negativa indica over-commitment

def test_fazenda_multiple_endividamentos(session):
    """Testa fazenda com múltiplos endividamentos."""
    fazenda = fazenda_exemplo("Fazenda Multi", "FAZ-003")
    endiv1 = endividamento_exemplo("PROP-001")
    endiv2 = endividamento_exemplo("PROP-002")

    session.add_all([fazenda, endiv1, endiv2])
    session.commit()

    # Primeiro endividamento - crédito
    vinculo1 = EndividamentoFazenda(
        endividamento=endiv1,
        fazenda=fazenda,
        hectares=Decimal("20.0"),
        tipo="objeto_credito",
        descricao="Primeiro financiamento"
    )
    
    # Segundo endividamento - crédito
    vinculo2 = EndividamentoFazenda(
        endividamento=endiv2,
        fazenda=fazenda,
        hectares=Decimal("15.0"),
        tipo="objeto_credito",
        descricao="Segundo financiamento"
    )
    
    session.add_all([vinculo1, vinculo2])
    session.commit()

    # Área total usada é a soma dos dois financiamentos
    assert fazenda.area_usada_credito == 35.0
    assert fazenda.area_disponivel_credito == 45.0  # 80 - 35
    assert fazenda.total_endividamentos == 2

    # Verificar que os vínculos são retornados corretamente
    vinculos = fazenda.endividamentos_vinculados
    assert len(vinculos) == 2
    propostas = [v.endividamento.numero_proposta for v in vinculos]
    assert "PROP-001" in propostas
    assert "PROP-002" in propostas