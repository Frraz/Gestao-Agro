# tests/test_api_documento.py

def test_criar_documento(client, pessoa_obj):
    payload = {
        "nome": "Documento Teste",
        "tipo": "Certidões",  # valor correto do Enum
        "data_emissao": "2025-06-20",
        "tipo_entidade": "PESSOA",
        "pessoa_id": pessoa_obj.id,
    }
    response = client.post("/api/documentos/", json=payload)
    print("Status:", response.status_code)
    print("Data:", response.get_data(as_text=True))
    assert response.status_code == 201, f"Status inesperado: {response.status_code} - {response.data}"
    data = response.get_json()
    assert data["nome"] == payload["nome"]
    assert data["tipo"] == payload["tipo"]

def test_criar_documento_faltando_campo_obrigatorio(client, pessoa_obj):
    """
    Testa tentativa de criação de documento com campo obrigatório faltando.
    Deve retornar erro 400 ou 422.
    """
    payload = {
        # "nome" está faltando
        "tipo": "Certidões",  # valor correto do Enum!
        "data_emissao": "2025-06-20",
        "tipo_entidade": "PESSOA",
        "pessoa_id": pessoa_obj.id,
    }
    response = client.post("/api/documentos/", json=payload)
    print("Status:", response.status_code)
    print("Data:", response.get_data(as_text=True))
    assert response.status_code in (400, 422), f"Status esperado 400 ou 422, recebeu: {response.status_code}"

def test_criar_documento_tipo_invalido(client, pessoa_obj):
    payload = {
        "nome": "Doc Inválido",
        "tipo": "TipoInexistente",  # Valor inválido
        "data_emissao": "2025-06-20",
        "tipo_entidade": "PESSOA",
        "pessoa_id": pessoa_obj.id,
    }
    response = client.post("/api/documentos/", json=payload)
    assert response.status_code in (400, 422)
    data = response.get_json()
    assert "inválido" in data.get("erro", "").lower()
    
def test_listar_documentos(client):
    """
    Testa listagem dos documentos via API.
    """
    response = client.get("/api/documentos/")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)