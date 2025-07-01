# API Documentation - Gestão Agro

Este documento descreve as APIs públicas do sistema de Gestão Agro, incluindo exemplos de uso e parâmetros disponíveis.

## Sumário

- [Busca de Pessoas](#busca-de-pessoas)
- [API de Pessoas](#api-de-pessoas)
- [API de Fazendas](#api-de-fazendas)
- [Cache e Performance](#cache-e-performance)

## Busca de Pessoas

### `GET /endividamentos/buscar-pessoas`

Busca pessoas por nome ou CPF/CNPJ com suporte a cache Redis e paginação avançada.

**Parâmetros de Query:**

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `q` | string | Sim | Termo de busca (mínimo 2 caracteres) |
| `page` | integer | Não | Número da página (padrão: 1) |
| `limit` | integer | Não | Itens por página (padrão: 10, máximo: 50) |

**Comportamento de Cache:**
- Resultados são armazenados em cache Redis por 5 minutos
- Cache é invalidado automaticamente quando pessoas são criadas, atualizadas ou excluídas
- Chave de cache: `buscar_pessoas:{termo}:{page}:{limit}`

**Resposta (Modo Compatível - sem paginação):**

```json
[
  {
    "id": 1,
    "nome": "João Silva",
    "cpf_cnpj": "12345678901",
    "cpf_cnpj_formatado": "123.456.789-01"
  },
  {
    "id": 2,
    "nome": "Maria Santos",
    "cpf_cnpj": "98765432100",
    "cpf_cnpj_formatado": "987.654.321-00"
  }
]
```

**Resposta (Modo Paginado - com parâmetros page/limit):**

```json
{
  "data": [
    {
      "id": 1,
      "nome": "João Silva",
      "cpf_cnpj": "12345678901",
      "cpf_cnpj_formatado": "123.456.789-01"
    },
    {
      "id": 2,
      "nome": "Maria Santos",
      "cpf_cnpj": "98765432100",
      "cpf_cnpj_formatado": "987.654.321-00"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 2,
    "has_next": false,
    "has_prev": false,
    "total_pages": 1
  }
}
```

**Exemplos de Uso:**

```bash
# Busca simples (compatível com versão anterior)
curl "http://localhost:5000/endividamentos/buscar-pessoas?q=João"

# Busca com paginação
curl "http://localhost:5000/endividamentos/buscar-pessoas?q=Silva&page=1&limit=5"

# Busca por CPF/CNPJ
curl "http://localhost:5000/endividamentos/buscar-pessoas?q=123.456"
```

**Códigos de Status:**
- `200`: Busca realizada com sucesso
- `400`: Parâmetros inválidos

---

## API de Pessoas

### `GET /api/pessoas/`

Lista todas as pessoas cadastradas no sistema.

**Resposta:**

```json
[
  {
    "id": 1,
    "nome": "João Silva",
    "cpf_cnpj": "12345678901",
    "email": "joao@email.com",
    "telefone": "(11) 99999-9999",
    "endereco": "Rua das Flores, 123",
    "fazendas": [
      {
        "id": 1,
        "nome": "Fazenda São João"
      }
    ]
  }
]
```

### `GET /api/pessoas/{id}`

Obtém detalhes de uma pessoa específica.

**Parâmetros de URL:**
- `id`: ID da pessoa

**Resposta:**

```json
{
  "id": 1,
  "nome": "João Silva",
  "cpf_cnpj": "12345678901",
  "email": "joao@email.com",
  "telefone": "(11) 99999-9999",
  "endereco": "Rua das Flores, 123",
  "fazendas": [
    {
      "id": 1,
      "nome": "Fazenda São João"
    }
  ]
}
```

### `POST /api/pessoas/`

Cria uma nova pessoa no sistema.

**Body da Requisição:**

```json
{
  "nome": "João Silva",
  "cpf_cnpj": "12345678901",
  "email": "joao@email.com",
  "telefone": "(11) 99999-9999",
  "endereco": "Rua das Flores, 123"
}
```

**Validações:**
- `nome`: Obrigatório
- `cpf_cnpj`: Obrigatório, deve ser único, formato válido (11 ou 14 dígitos)
- `email`: Opcional, deve conter @
- `telefone`: Opcional
- `endereco`: Opcional

**Resposta (201 Created):**

```json
{
  "id": 1,
  "nome": "João Silva",
  "cpf_cnpj": "12345678901",
  "email": "joao@email.com",
  "telefone": "(11) 99999-9999",
  "endereco": "Rua das Flores, 123"
}
```

**Efeitos Colaterais:**
- Invalida cache de busca de pessoas
- Gera log de auditoria

### `PUT /api/pessoas/{id}`

Atualiza os dados de uma pessoa existente.

**Parâmetros de URL:**
- `id`: ID da pessoa

**Body da Requisição:**

```json
{
  "nome": "João Silva Santos",
  "email": "joao.santos@email.com",
  "telefone": "(11) 88888-8888"
}
```

**Resposta (200 OK):**

```json
{
  "id": 1,
  "nome": "João Silva Santos",
  "cpf_cnpj": "12345678901",
  "email": "joao.santos@email.com",
  "telefone": "(11) 88888-8888",
  "endereco": "Rua das Flores, 123"
}
```

**Efeitos Colaterais:**
- Invalida cache de busca de pessoas
- Gera log de auditoria

### `DELETE /api/pessoas/{id}`

Exclui uma pessoa do sistema.

**Parâmetros de URL:**
- `id`: ID da pessoa

**Resposta (200 OK):**

```json
{
  "mensagem": "Pessoa João Silva excluída com sucesso"
}
```

**Restrições:**
- Não é possível excluir pessoa com documentos associados
- Associações com fazendas são removidas automaticamente

**Efeitos Colaterais:**
- Invalida cache de busca de pessoas
- Remove associações com fazendas
- Gera log de auditoria

---

## API de Fazendas

### `GET /endividamentos/api/fazendas/{pessoa_id}`

Obtém fazendas associadas a uma pessoa específica.

**Parâmetros de URL:**
- `pessoa_id`: ID da pessoa

**Resposta:**

```json
[
  {
    "id": 1,
    "nome": "Fazenda São João",
    "tamanho_total": 100.5
  }
]
```

---

## Cache e Performance

### Estratégia de Cache

O sistema utiliza Redis para cache de consultas frequentes:

**Tipos de Cache:**
1. **Cache de Busca**: Resultados de busca de pessoas (`buscar_pessoas:*`)
2. **Cache de Seleção**: Listas para selects (`pessoas:*`, `fazendas:*`)
3. **Cache de Dashboard**: Dados do painel (`dashboard:*`)

**Invalidação de Cache:**
- **Automática**: Quando entidades são criadas, atualizadas ou excluídas
- **Padrões de Invalidação**:
  - Pessoa: `["pessoas:*", "buscar_pessoas:*", "dashboard:*"]`
  - Fazenda: `["fazendas:*", "dashboard:*"]`
  - Documento: `["dashboard:*"]`
  - Endividamento: `["dashboard:*"]`

**Configuração:**
- Tempo de cache padrão: 5 minutos (300 segundos)
- URL Redis: Configurável via `REDIS_URL` (padrão: `redis://localhost:6379/0`)
- Fallback: Sistema funciona sem Redis se conexão falhar

### Boas Práticas

1. **Use paginação** para grandes conjuntos de dados
2. **Limite o tamanho das páginas** (máximo 50 itens)
3. **Considere o cache** ao projetar consultas frequentes
4. **Monitore logs** para identificar problemas de performance

### Exemplos de Uso Otimizado

```javascript
// Frontend: Busca com cache e paginação
async function buscarPessoas(termo, page = 1) {
  const response = await fetch(
    `/endividamentos/buscar-pessoas?q=${encodeURIComponent(termo)}&page=${page}&limit=10`
  );
  return response.json();
}

// Backend: Cache manual
from src.utils.cache import cache

def funcao_com_cache():
    cache_key = "minha_funcao:params"
    result = cache.get(cache_key)
    if result is None:
        result = operacao_custosa()
        cache.set(cache_key, result, timeout=600)
    return result
```

---

## Códigos de Erro Comuns

| Código | Descrição |
|--------|-----------|
| 400 | Parâmetros inválidos ou dados malformados |
| 404 | Recurso não encontrado |
| 500 | Erro interno do servidor |

## Versionamento

A API mantém compatibilidade com versões anteriores:
- Endpoints sem parâmetros de paginação retornam formato antigo
- Novos parâmetros são opcionais
- Comportamentos existentes são preservados