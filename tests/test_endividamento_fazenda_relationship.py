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

def test_endividamento_fazenda_relationship(session):
    fazenda1 = fazenda_exemplo("Fazenda Sol", "FAZ-001")
    fazenda2 = fazenda_exemplo("Fazenda Lua", "FAZ-002")
    endiv = endividamento_exemplo("PROP-123")

    session.add_all([fazenda1, fazenda2, endiv])
    session.commit()

    # Associa o endividamento às fazendas via EndividamentoFazenda
    vinculo1 = EndividamentoFazenda(
        endividamento=endiv,
        fazenda=fazenda1,
        hectares=Decimal("55.5"),
        tipo="objeto_credito",
        descricao="Financia plantio"
    )
    vinculo2 = EndividamentoFazenda(
        endividamento=endiv,
        fazenda=fazenda2,
        hectares=Decimal("44.5"),
        tipo="garantia",
        descricao="Garantia hipotecária"
    )

    session.add_all([vinculo1, vinculo2])
    session.commit()

    # Verifica do lado do endividamento
    endiv_db = Endividamento.query.filter_by(numero_proposta="PROP-123").first()
    assert len(endiv_db.fazenda_vinculos) == 2
    nomes_fazendas = [v.fazenda.nome for v in endiv_db.fazenda_vinculos]
    assert "Fazenda Sol" in nomes_fazendas
    assert "Fazenda Lua" in nomes_fazendas

    # Verifica os dados extras do vínculo
    objeto = next(v for v in endiv_db.fazenda_vinculos if v.tipo == "objeto_credito")
    garantia = next(v for v in endiv_db.fazenda_vinculos if v.tipo == "garantia")
    assert objeto.hectares == Decimal("55.5")
    assert garantia.hectares == Decimal("44.5")
    assert objeto.descricao == "Financia plantio"
    assert garantia.descricao == "Garantia hipotecária"

    # Verifica do lado da fazenda
    faz1_db = Fazenda.query.filter_by(matricula="FAZ-001").first()
    faz2_db = Fazenda.query.filter_by(matricula="FAZ-002").first()
    # Não existe backref pronto no model Fazenda, mas podemos consultar EndividamentoFazenda
    vinc_faz1 = EndividamentoFazenda.query.filter_by(fazenda_id=faz1_db.id).all()
    assert len(vinc_faz1) == 1
    assert vinc_faz1[0].endividamento.numero_proposta == "PROP-123"