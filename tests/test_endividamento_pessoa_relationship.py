import pytest
from datetime import date
from decimal import Decimal
from src.main import create_app
from src.models.db import db
from src.models.pessoa import Pessoa
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

def pessoa_exemplo(nome, cpf_cnpj):
    return Pessoa(
        nome=nome,
        cpf_cnpj=cpf_cnpj,
        email=f"{nome.lower().replace(' ', '')}@teste.com"
    )

def endividamento_exemplo(numero_proposta="PROP-1"):
    return Endividamento(
        banco="Banco Teste",
        numero_proposta=numero_proposta,
        data_emissao=date(2024, 1, 1),
        data_vencimento_final=date(2025, 1, 1),
        taxa_juros=Decimal("10.50"),
        tipo_taxa_juros="ano",
        prazo_carencia=6,
        valor_operacao=Decimal("100000.00")
    )

def test_endividamento_pessoa_relationship(session):
    # Cria duas pessoas e dois endividamentos
    pessoa1 = pessoa_exemplo("João", "11111111111")
    pessoa2 = pessoa_exemplo("Maria", "22222222222")
    endiv1 = endividamento_exemplo("PROP-1")
    endiv2 = endividamento_exemplo("PROP-2")
    
    # Associa ambos os endividamentos a ambas as pessoas
    pessoa1.endividamentos.append(endiv1)
    pessoa1.endividamentos.append(endiv2)
    pessoa2.endividamentos.append(endiv2)  # só Maria tem o segundo endividamento também

    session.add_all([pessoa1, pessoa2, endiv1, endiv2])
    session.commit()
    
    # Verifica do lado da Pessoa
    joao = Pessoa.query.filter_by(cpf_cnpj="11111111111").first()
    maria = Pessoa.query.filter_by(cpf_cnpj="22222222222").first()
    assert len(joao.endividamentos) == 2
    assert len(maria.endividamentos) == 1
    assert maria.endividamentos[0].numero_proposta == "PROP-2"

    # Verifica do lado do Endividamento
    prop1 = Endividamento.query.filter_by(numero_proposta="PROP-1").first()
    prop2 = Endividamento.query.filter_by(numero_proposta="PROP-2").first()
    assert len(prop1.pessoas) == 1
    assert prop1.pessoas[0].nome == "João"
    assert len(prop2.pessoas) == 2
    nomes = [p.nome for p in prop2.pessoas]
    assert "João" in nomes and "Maria" in nomes