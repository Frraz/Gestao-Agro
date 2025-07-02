# tests/test_api_fazenda.py


import unicodedata

def normalize_enum(val):
    # Garante que None não quebre a normalização
    if val is None:
        return ""
    return unicodedata.normalize('NFKD', val).encode('ASCII', 'ignore').decode().upper()

def test_criar_listar_fazenda(client):
    response = client.get("/api/fazendas/")
    assert response.status_code == 200
    assert isinstance(response.get_json(), list)
    assert len(response.get_json()) == 0

    payload = {
        "nome": "Fazenda Teste",
        "matricula": "123",
        "tamanho_total": 100.0,
        "area_consolidada": 20.0,
        "tipo_posse": "Própria",
        "municipio": "Cidade X",
        "estado": "UF",
        "recibo_car": "CAR-001"
    }
    response = client.post("/api/fazendas/", json=payload)
    assert response.status_code == 201, f"Retorno: {response.status_code}, body: {response.get_json()}"
    data = response.get_json()
    assert data["nome"] == payload["nome"]
    # Compara normalizando ambos (caso backend mude futura serialização para .name)
    assert normalize_enum(data["tipo_posse"]) == normalize_enum("PROPRIA")
    fazenda_id = data["id"]

    response = client.get("/api/fazendas/")
    assert response.status_code == 200
    data_list = response.get_json()
    assert any(f["id"] == fazenda_id for f in data_list)

def test_get_update_delete_fazenda(client):
    payload = {
        "nome": "Fazenda API",
        "matricula": "456",
        "tamanho_total": 150.0,
        "area_consolidada": 30.0,
        "tipo_posse": "Própria",
        "municipio": "Cidade Y",
        "estado": "UF",
        "recibo_car": "CAR-002"
    }
    response = client.post("/api/fazendas/", json=payload)
    assert response.status_code == 201, f"Retorno: {response.status_code}, body: {response.get_json()}"
    data = response.get_json()
    fazenda_id = data["id"]

    response = client.get(f"/api/fazendas/{fazenda_id}")
    assert response.status_code == 200
    data_get = response.get_json()
    assert data_get["nome"] == payload["nome"]
    assert normalize_enum(data_get["tipo_posse"]) == normalize_enum("PROPRIA")

    response = client.put(f"/api/fazendas/{fazenda_id}", json={
        "municipio": "Cidade Alterada"
    })
    assert response.status_code == 200
    assert response.get_json()["municipio"] == "Cidade Alterada"

    response = client.delete(f"/api/fazendas/{fazenda_id}")
    assert response.status_code == 200
    assert "excluída com sucesso" in response.get_json().get("mensagem", "")

    response = client.get(f"/api/fazendas/{fazenda_id}")
    assert response.status_code == 404

def test_criar_fazenda_faltando_nome(client):
    payload = {
        "matricula": "123",
        "tamanho_total": 100.0,
        "area_consolidada": 20.0,
        "tipo_posse": "Própria",
        "municipio": "Cidade X",
        "estado": "UF",
        "recibo_car": "CAR-001"
    }
    response = client.post("/api/fazendas/", json=payload)
    # Exibe o status para entender eventual erro
    assert response.status_code in (400, 422), f"Status inesperado: {response.status_code}, body: {response.get_json()}"

def test_update_fazenda_inexistente(client):
    response = client.put("/api/fazendas/9999", json={"municipio": "X"})
    assert response.status_code == 404, f"Status inesperado: {response.status_code}, body: {response.get_json()}"

def test_delete_fazenda_inexistente(client):
    response = client.delete("/api/fazendas/9999")
    assert response.status_code == 404, f"Status inesperado: {response.status_code}, body: {response.get_json()}"