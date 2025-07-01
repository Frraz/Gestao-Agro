# Cache e Paginação - Exemplos de Uso

Este documento fornece exemplos práticos de como utilizar as novas funcionalidades de cache Redis e paginação no endpoint de busca de pessoas.

## Frontend JavaScript

### Busca Simples (Compatível com Versão Anterior)

```javascript
// Funcionalidade existente continua funcionando
async function buscarPessoas() {
    const termo = document.getElementById('buscaPessoa').value;
    
    if (termo.length < 2) return;
    
    const response = await fetch(`/endividamentos/buscar-pessoas?q=${encodeURIComponent(termo)}`);
    const pessoas = await response.json();
    
    // pessoas é um array como antes
    pessoas.forEach(pessoa => {
        console.log(pessoa.nome, pessoa.cpf_cnpj_formatado);
    });
}
```

### Busca com Paginação

```javascript
class BuscaPessoas {
    constructor() {
        this.currentPage = 1;
        this.limit = 10;
    }
    
    async buscar(termo, page = 1) {
        const url = `/endividamentos/buscar-pessoas?q=${encodeURIComponent(termo)}&page=${page}&limit=${this.limit}`;
        const response = await fetch(url);
        const data = await response.json();
        
        // data.data contém os resultados
        // data.pagination contém metadados
        this.renderResultados(data.data);
        this.renderPaginacao(data.pagination);
        
        return data;
    }
    
    renderResultados(pessoas) {
        const container = document.getElementById('resultados');
        container.innerHTML = '';
        
        pessoas.forEach(pessoa => {
            const div = document.createElement('div');
            div.innerHTML = `
                <div class="pessoa-item">
                    <strong>${pessoa.nome}</strong>
                    <small>${pessoa.cpf_cnpj_formatado}</small>
                </div>
            `;
            container.appendChild(div);
        });
    }
    
    renderPaginacao(pagination) {
        const container = document.getElementById('paginacao');
        container.innerHTML = '';
        
        // Botão anterior
        if (pagination.has_prev) {
            const btnPrev = document.createElement('button');
            btnPrev.textContent = 'Anterior';
            btnPrev.onclick = () => this.buscar(this.lastTerm, pagination.page - 1);
            container.appendChild(btnPrev);
        }
        
        // Informações da página
        const info = document.createElement('span');
        info.textContent = `Página ${pagination.page} de ${pagination.total_pages} (${pagination.total} resultados)`;
        container.appendChild(info);
        
        // Botão próximo
        if (pagination.has_next) {
            const btnNext = document.createElement('button');
            btnNext.textContent = 'Próximo';
            btnNext.onclick = () => this.buscar(this.lastTerm, pagination.page + 1);
            container.appendChild(btnNext);
        }
    }
}

// Uso
const buscador = new BuscaPessoas();
```

### Busca com Debounce e Cache Cliente

```javascript
class BuscaAvancada {
    constructor() {
        this.cache = new Map();
        this.debounceTimer = null;
    }
    
    debounce(func, wait) {
        return (...args) => {
            clearTimeout(this.debounceTimer);
            this.debounceTimer = setTimeout(() => func.apply(this, args), wait);
        };
    }
    
    async buscarComCache(termo, page = 1, limit = 10) {
        const cacheKey = `${termo}_${page}_${limit}`;
        
        // Verificar cache cliente
        if (this.cache.has(cacheKey)) {
            return this.cache.get(cacheKey);
        }
        
        const url = `/endividamentos/buscar-pessoas?q=${encodeURIComponent(termo)}&page=${page}&limit=${limit}`;
        const response = await fetch(url);
        const data = await response.json();
        
        // Armazenar no cache cliente por 2 minutos
        this.cache.set(cacheKey, data);
        setTimeout(() => this.cache.delete(cacheKey), 120000);
        
        return data;
    }
    
    // Função com debounce para usar no input
    buscarDebounced = this.debounce(this.buscarComCache, 300);
}
```

## Backend Python

### Uso Direto do Cache

```python
from src.utils.cache import cache

def funcao_personalizada():
    """Exemplo de uso do cache em outras funções"""
    cache_key = "minha_funcao:parametros"
    
    # Tentar obter do cache
    resultado = cache.get(cache_key)
    if resultado is not None:
        return resultado
    
    # Executar operação custosa
    resultado = operacao_custosa()
    
    # Armazenar no cache por 10 minutos
    cache.set(cache_key, resultado, timeout=600)
    
    return resultado

def invalidar_cache_personalizado():
    """Invalidar cache específico"""
    from src.utils.cache import cache
    
    # Invalidar chave específica
    cache.delete("minha_funcao:parametros")
    
    # Invalidar padrão
    cache.clear_pattern("minha_funcao:*")
```

### Implementar Endpoint com Cache

```python
from flask import Blueprint, request, jsonify
from src.utils.cache import cache

meu_bp = Blueprint('meu_endpoint', __name__)

@meu_bp.route('/meu-endpoint')
def meu_endpoint_com_cache():
    """Exemplo de endpoint com cache"""
    param = request.args.get('param', '')
    page = request.args.get('page', 1, type=int)
    
    # Gerar chave de cache
    cache_key = f"meu_endpoint:{param}:{page}"
    
    # Tentar cache
    resultado = cache.get(cache_key)
    if resultado is not None:
        return jsonify(resultado)
    
    # Processar dados
    dados = processar_dados(param, page)
    
    # Armazenar no cache
    cache.set(cache_key, dados, timeout=300)
    
    return jsonify(dados)
```

## Monitoramento e Debug

### Verificar Status do Cache

```python
def verificar_cache():
    """Função para debug do cache"""
    from src.utils.cache import cache
    
    if cache.redis_client:
        try:
            info = cache.redis_client.info()
            print(f"Redis conectado: {info['redis_version']}")
            print(f"Chaves ativas: {cache.redis_client.dbsize()}")
            
            # Listar chaves de busca
            keys = cache.redis_client.keys("buscar_pessoas:*")
            print(f"Chaves de busca ativas: {len(keys)}")
            
        except Exception as e:
            print(f"Erro ao verificar Redis: {e}")
    else:
        print("Redis não conectado")
```

### Limpar Cache Manualmente

```python
def limpar_cache_desenvolvimento():
    """Limpar todo o cache para desenvolvimento"""
    from src.utils.cache import cache
    
    if cache.redis_client:
        # Limpar apenas chaves do projeto
        patterns = [
            "buscar_pessoas:*",
            "pessoas:*", 
            "fazendas:*",
            "dashboard:*"
        ]
        
        for pattern in patterns:
            keys = cache.redis_client.keys(pattern)
            if keys:
                cache.redis_client.delete(*keys)
                print(f"Limpas {len(keys)} chaves do padrão {pattern}")
```

## Configuração de Produção

### Variáveis de Ambiente

```bash
# .env
REDIS_URL=redis://localhost:6379/0
# ou para Redis com autenticação
REDIS_URL=redis://:password@redis-host:6379/0
```

### Docker Compose

```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
  
  app:
    build: .
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis

volumes:
  redis_data:
```

## Métricas e Performance

### Monitorar Performance

```python
import time
from functools import wraps

def medir_performance(func):
    """Decorator para medir performance"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        resultado = func(*args, **kwargs)
        fim = time.time()
        
        print(f"{func.__name__} executada em {fim - start:.3f}s")
        return resultado
    
    return wrapper

# Uso
@medir_performance
def busca_sem_cache():
    # Busca direta no banco
    pass
```

### Estatísticas de Cache

```python
def estatisticas_cache():
    """Obter estatísticas do cache"""
    from src.utils.cache import cache
    
    if not cache.redis_client:
        return {"status": "desconectado"}
    
    info = cache.redis_client.info()
    
    return {
        "hits": info.get('keyspace_hits', 0),
        "misses": info.get('keyspace_misses', 0),
        "hit_rate": info.get('keyspace_hits', 0) / max(1, info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0)),
        "memory_used": info.get('used_memory_human', '0B'),
        "connected_clients": info.get('connected_clients', 0),
        "total_keys": cache.redis_client.dbsize()
    }
```