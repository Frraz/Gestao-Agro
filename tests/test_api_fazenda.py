import pytest
from src.main import create_app
from src.models.db import db
from src.models.fazenda import TipoPosse

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
def client(app):
    return app.test_client()

def test_criar_listar_fazenda(client):
    # Cria uma fazenda via POST
    response = client.post("/api/fazendas/", json={
        "nome": "Fazenda Teste",
        "matricula": "123",
        "tamanho_total": 100.0,
        "area_consolidada": 20.0,
        "tipo_posse": TipoPosse.PROPRIA.value,
        "municipio": "Cidade X",
        "estado": "UF",
        "recibo_car": "CAR-001"
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data["nome"] == "Fazenda Teste"
    fazenda_id = data["id"]

    # Lista fazendas via GET (com barra final)
    response = client.get("/api/fazendas/")
    assert response.status_code == 200
    data_list = response.get_json()
    assert any(f["id"] == fazenda_id for f in data_list)

def test_get_update_delete_fazenda(client):
    # Cria uma fazenda
    response = client.post("/api/fazendas/", json={
        "nome": "Fazenda API",
        "matricula": "456",
        "tamanho_total": 150.0,
        "area_consolidada": 30.0,
        "tipo_posse": TipoPosse.PROPRIA.value,
        "municipio": "Cidade Y",
        "estado": "UF",
        "recibo_car": "CAR-002"
    })
    fazenda_id = response.get_json()["id"]

    # GET único
    response = client.get(f"/api/fazendas/{fazenda_id}")
    assert response.status_code == 200
    assert response.get_json()["nome"] == "Fazenda API"

    # PUT (atualiza parcialmente)
    response = client.put(f"/api/fazendas/{fazenda_id}", json={
        "municipio": "Cidade Alterada"
    })
    assert response.status_code == 200
    assert response.get_json()["municipio"] == "Cidade Alterada"

    # DELETE
    response = client.delete(f"/api/fazendas/{fazenda_id}")
    assert response.status_code == 200
    assert "excluída com sucesso" in response.get_json().get("mensagem", "")

    # GET após deleção deve retornar 404
    response = client.get(f"/api/fazendas/{fazenda_id}")
    assert response.status_code == 404