# tests/test_api_documento.py

def test_criar_documento(client, pessoa_obj):
    payload = {
        "nome": "Documento Teste",
        "tipo": "Certidões",
        "data_emissao": "2025-06-20",
        "tipo_entidade": "PESSOA",
        "pessoa_id": pessoa_obj.id,
    }
    response = client.post("/api/documentos/", json=payload)
    assert response.status_code == 201, f"Status inesperado: {response.status_code} - {response.data}"
    data = response.get_json()
    for field in payload:
        if field == "tipo_entidade":
            # Aceita valores como "Pessoa" ou "PESSOA" (caso padronizado no Enum.name)
            assert data[field].upper() == payload[field].upper(), (
                f'Divergência no campo tipo_entidade: esperado {payload[field]}, recebido {data[field]}'
            )
        else:
            assert data[field] == payload[field], f'Divergência no campo {field}: esperado {payload[field]}, recebido {data[field]}'

def test_criar_documento_faltando_campo_obrigatorio(client, pessoa_obj):
    payload = {
        # "nome" está faltando
        "tipo": "Certidões",
        "data_emissao": "2025-06-20",
        "tipo_entidade": "PESSOA",
        "pessoa_id": pessoa_obj.id,
    }
    response = client.post("/api/documentos/", json=payload)
    assert response.status_code in (400, 422), f"Status esperado 400 ou 422, recebeu: {response.status_code}"

def test_criar_documento_tipo_invalido(client, pessoa_obj):
    payload = {
        "nome": "Doc Inválido",
        "tipo": "TipoInexistente",
        "data_emissao": "2025-06-20",
        "tipo_entidade": "PESSOA",
        "pessoa_id": pessoa_obj.id,
    }
    response = client.post("/api/documentos/", json=payload)
    assert response.status_code in (400, 422)
    data = response.get_json()
    assert "inválido" in (data.get("erro") or data.get("error") or "").lower()

def test_listar_documentos(client, pessoa_obj):
    # Garante pelo menos um documento
    payload = {
        "nome": "Documento Listagem",
        "tipo": "Certidões",
        "data_emissao": "2025-06-20",
        "tipo_entidade": "PESSOA",
        "pessoa_id": pessoa_obj.id,
    }
    client.post("/api/documentos/", json=payload)
    response = client.get("/api/documentos/")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert any(doc["nome"] == "Documento Listagem" for doc in data)