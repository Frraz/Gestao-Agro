# /src/utils/cache.py

"""
Gerenciador de cache com Redis
Fornece cache distribuído para melhorar performance do sistema
"""

import pickle

import redis
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError
from flask import current_app, request


class CacheManager:
    """Gerenciador de cache usando Redis com recursos avançados"""

    def __init__(self, app=None):
        self.redis_client = None
        self.prefix = "gestao_agro:"
        self.default_timeout = 300  # 5 minutos
        self.stats = {
            'hits': 0,
            'misses': 0,
            'errors': 0
        }
        
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Inicializa o cache com a aplicação Flask"""
        redis_url = app.config.get("REDIS_URL", "redis://localhost:6379/0")
        self.prefix = app.config.get("CACHE_KEY_PREFIX", "gestao_agro:")
        self.default_timeout = app.config.get("CACHE_DEFAULT_TIMEOUT", 300)
        
        try:
            # Configurar pool de conexões
            pool = redis.ConnectionPool.from_url(
                redis_url,
                max_connections=app.config.get("REDIS_MAX_CONNECTIONS", 50),
                socket_keepalive=True,
                socket_keepalive_options={},
                retry_on_timeout=True,
                decode_responses=False
            )
            
            self.redis_client = redis.Redis(connection_pool=pool)
            
            # Testar conexão
            self.redis_client.ping()
            app.logger.info("Cache Redis conectado com sucesso")
            
            # Registrar comandos de gerenciamento
            self._register_commands(app)
            
        except Exception as e:
            app.logger.warning(f"Não foi possível conectar ao Redis: {e}")
            self.redis_client = None

    def _make_key(self, key: str) -> str:
        """Cria chave com prefixo"""
        return f"{self.prefix}{key}"

    def get(self, key: str, default: Any = None) -> Any:
        """Recupera valor do cache"""
        if not self.redis_client:
            return default

        try:
            full_key = self._make_key(key)
            value = self.redis_client.get(full_key)
            
            if value:
                self.stats['hits'] += 1
                return pickle.loads(value)
            else:
                self.stats['misses'] += 1
                return default
                
        except Exception as e:
            self.stats['errors'] += 1
            if current_app:
                current_app.logger.error(f"Erro ao recuperar cache {key}: {e}")
            return default

    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """Armazena valor no cache"""
        if not self.redis_client:
            return False

        try:
            full_key = self._make_key(key)
            serialized_value = pickle.dumps(value)
            timeout = timeout or self.default_timeout
            
            return self.redis_client.setex(full_key, timeout, serialized_value)
            
        except Exception as e:
            self.stats['errors'] += 1
            if current_app:
                current_app.logger.error(f"Erro ao armazenar cache {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Remove valor do cache"""
        if not self.redis_client:
            return False

        try:
            full_key = self._make_key(key)
            return bool(self.redis_client.delete(full_key))
            
        except Exception as e:
            self.stats['errors'] += 1
            if current_app:
                current_app.logger.error(f"Erro ao deletar cache {key}: {e}")
            return False

    def clear_pattern(self, pattern: str) -> int:
        """Remove todas as chaves que correspondem ao padrão
        
        Args:
            pattern: Padrão para correspondência (ex: user_*)
            
        Returns:
            Número de chaves removidas
        """
        if not self.redis_client:
            return 0

        try:
            full_pattern = f"{self.prefix}{pattern}"
            
            # Usar SCAN para evitar bloqueio em grandes conjuntos
            deleted = 0
            for key in self.redis_client.scan_iter(match=full_pattern, count=100):
                self.redis_client.delete(key)
                deleted += 1
                
            if current_app:
                current_app.logger.info(f"Removidas {deleted} chaves com padrão {pattern}")
                
            return deleted
            
        except Exception as e:
            self.stats['errors'] += 1
            if current_app:
                current_app.logger.error(f"Erro ao limpar cache com padrão {pattern}: {e}")
            return 0

    def clear(self) -> bool:
        """Limpa todo o cache (use com cuidado!)"""
        return self.clear_pattern("*") > 0

    def exists(self, key: str) -> bool:
        """Verifica se uma chave existe"""
        if not self.redis_client:
            return False
            
        try:
            full_key = self._make_key(key)
            return bool(self.redis_client.exists(full_key))
        except:
            return False

    def ttl(self, key: str) -> int:
        """Retorna o tempo de vida restante de uma chave em segundos"""
        if not self.redis_client:
            return -1
            
        try:
            full_key = self._make_key(key)
            return self.redis_client.ttl(full_key)
        except:
            return -1

    def set_many(self, mapping: Dict[str, Any], timeout: Optional[int] = None) -> bool:
        """Armazena múltiplos valores de uma vez"""
        if not self.redis_client:
            return False
            
        try:
            timeout = timeout or self.default_timeout
            pipe = self.redis_client.pipeline()
            
            for key, value in mapping.items():
                full_key = self._make_key(key)
                serialized_value = pickle.dumps(value)
                pipe.setex(full_key, timeout, serialized_value)
                
            pipe.execute()
            return True
            
        except Exception as e:
            self.stats['errors'] += 1
            if current_app:
                current_app.logger.error(f"Erro ao armazenar múltiplos valores: {e}")
            return False

    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Recupera múltiplos valores de uma vez"""
        if not self.redis_client:
            return {}
            
        try:
            full_keys = [self._make_key(key) for key in keys]
            values = self.redis_client.mget(full_keys)
            
            result = {}
            for key, value in zip(keys, values):
                if value:
                    result[key] = pickle.loads(value)
                    self.stats['hits'] += 1
                else:
                    self.stats['misses'] += 1
                    
            return result
            
        except Exception as e:
            self.stats['errors'] += 1
            if current_app:
                current_app.logger.error(f"Erro ao recuperar múltiplos valores: {e}")
            return {}

    def increment(self, key: str, delta: int = 1) -> Optional[int]:
        """Incrementa um valor numérico"""
        if not self.redis_client:
            return None
            
        try:
            full_key = self._make_key(key)
            return self.redis_client.incrby(full_key, delta)
        except:
            return None

    def get_stats(self) -> Dict[str, int]:
        """Retorna estatísticas do cache"""
        total = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total * 100) if total > 0 else 0
        
        return {
            **self.stats,
            'total_requests': total,
            'hit_rate': round(hit_rate, 2)
        }

    @contextmanager
    def lock(self, key: str, timeout: int = 10):
        """Context manager para lock distribuído"""
        if not self.redis_client:
            yield False
            return
            
        lock_key = f"lock:{self._make_key(key)}"
        lock_value = f"{datetime.now().timestamp()}"
        
        try:
            # Tentar adquirir o lock
            acquired = self.redis_client.set(lock_key, lock_value, nx=True, ex=timeout)
            yield acquired
        finally:
            # Liberar o lock apenas se ainda for nosso
            if acquired:
                current_value = self.redis_client.get(lock_key)
                if current_value and current_value.decode() == lock_value:
                    self.redis_client.delete(lock_key)

    def _register_commands(self, app):
        """Registra comandos CLI para gerenciamento do cache"""
        @app.cli.command()
        def clear_cache():
            """Limpa todo o cache Redis"""
            if self.clear():
                print("Cache limpo com sucesso!")
            else:
                print("Erro ao limpar cache")
                
        @app.cli.command()
        def cache_stats():
            """Mostra estatísticas do cache"""
            stats = self.get_stats()
            print(f"Cache Statistics:")
            print(f"  Hits: {stats['hits']}")
            print(f"  Misses: {stats['misses']}")
            print(f"  Errors: {stats['errors']}")
            print(f"  Hit Rate: {stats['hit_rate']}%")


# Instância global do cache
cache = CacheManager()


def cached(timeout=300, key_prefix=""):
    """Decorator para cache de funções"""


    def decorator(f):


        def wrapper(*args, **kwargs):
            # Verificar se deve pular o cache
            if unless and unless():
                return f(*args, **kwargs)
                
            # Gerar chave do cache
            cache_key_parts = [key_prefix or f.__module__, f.__name__]
            
            # Adicionar argumentos à chave
            if args:
                args_str = str(args)
                cache_key_parts.append(hashlib.md5(args_str.encode()).hexdigest()[:8])
            if kwargs:
                kwargs_str = json.dumps(kwargs, sort_keys=True)
                cache_key_parts.append(hashlib.md5(kwargs_str.encode()).hexdigest()[:8])
                
            cache_key = ":".join(cache_key_parts)
            
            # Verificar se deve forçar atualização
            if forced_update and forced_update():
                result = f(*args, **kwargs)
                cache.set(cache_key, result, timeout)
                return result
            
            # Tentar recuperar do cache
            result = cache.get(cache_key)
            if result is not None:
                return result

            # Executar função e armazenar no cache
            result = f(*args, **kwargs)
            cache.set(cache_key, result, timeout)

            return result

        wrapper.__name__ = f.__name__
        wrapper.__cached__ = True
        return wrapper

    return decorator


def cached_property(timeout: Optional[int] = None, key_prefix: str = ""):
    """Decorator para cache de propriedades"""
    def decorator(f):
        attr_name = f'_cached_{f.__name__}'
        
        @wraps(f)
        def wrapper(self):
            # Verificar cache local primeiro
            if hasattr(self, attr_name):
                return getattr(self, attr_name)
                
            # Gerar chave do cache
            cache_key = f"{key_prefix}:{self.__class__.__name__}:{f.__name__}:{id(self)}"
            
            # Tentar recuperar do cache Redis
            result = cache.get(cache_key)
            if result is not None:
                setattr(self, attr_name, result)
                return result
                
            # Executar método e cachear
            result = f(self)
            cache.set(cache_key, result, timeout)
            setattr(self, attr_name, result)
            
            return result
            
        return property(wrapper)
        
    return decorator


def invalidate_cache(pattern: str):
    """Decorator para invalidar cache quando uma função é executada"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            result = f(*args, **kwargs)
            cache.clear_pattern(pattern)
            return result
        return wrapper
    return decorator


# Função que estava faltando e causando o erro de importação
def cache_clear_pattern(pattern: str) -> Dict[str, Any]:
    """
    Limpa todas as entradas de cache que correspondam a um padrão.
    
    Args:
        pattern: Padrão para corresponder às chaves de cache (ex: 'user_*')
        
    Returns:
        Dicionário com informações sobre as chaves limpas
    """
    try:
        cleared_count = cache.clear_pattern(pattern)
        return {
            "status": "success",
            "pattern": pattern,
            "cleared_count": cleared_count,
            "cleared_keys": [pattern]  # Representação simplificada das chaves limpas
        }
    except Exception as e:
        if current_app:
            current_app.logger.error(f"Erro ao limpar cache com padrão {pattern}: {e}")
        return {
            "status": "error",
            "pattern": pattern,
            "error": str(e),
            "cleared_count": 0,
            "cleared_keys": []
        }


# Cache específico para queries de banco
def cache_query(timeout: int = 300):
    """Decorator específico para cache de queries"""
    return cached(
        timeout=timeout,
        key_prefix="query",
        unless=lambda: request and request.method != 'GET'
    )


# Exportar funções principais
__all__ = [
    'cache',
    'cached',
    'cached_property',
    'invalidate_cache',
    'cache_query',
    'CacheManager',
    'cache_clear_pattern'  # Adicionada à lista de exportação
]