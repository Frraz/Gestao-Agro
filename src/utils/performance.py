# /src/utils/performance.py

"""
Utilitários para otimização de performance do sistema.

Este módulo fornece classes e funções para otimizar o desempenho do sistema,
incluindo cache, otimizações de banco de dados, rate limiting, métricas de desempenho
e monitoramento de tempos de execução.
"""

import logging
import re
import time
import json
import threading
from typing import Dict, Any, Callable, List, Optional
from flask import request, g
from functools import wraps
from typing import Any, Dict, List, Optional, Set, Union, Callable, TypeVar

from flask import current_app, jsonify, request, Response, g
from sqlalchemy import text, func, and_, or_, event
from sqlalchemy.engine import Engine
from datetime import date, datetime, timedelta

from src.models.db import db
from src.utils.cache import cache, cached
from src.utils.cache import cache_clear_pattern

logger = logging.getLogger(__name__)

# Definindo tipos para os decoradores
F = TypeVar('F', bound=Callable[..., Any])

# Métricas globais
performance_metrics = {
    "notificacoes_enviadas": 0,
    "tempo_medio_envio_ms": 0,
    "falhas_envio": 0,
    "queries_lentas": [],
    "funcoes_lentas": []
}


class PerformanceOptimizer:
    """Classe para otimizações de performance"""

    @staticmethod
    def optimize_database_queries() -> bool:
        """
        Otimiza configurações do banco de dados
        
        Returns:
            bool: True se as otimizações foram aplicadas com sucesso
        """
        try:
            engine = db.engine
            backend = engine.url.get_backend_name()
            logger.info(f"Backend do banco detectado: {backend}")
            
            # Configurações específicas por tipo de banco
            if "mysql" in backend:
                # Detecta versão do MySQL
                version = db.session.execute(text("SELECT VERSION()")).scalar()
                logger.info(f"MySQL version detected: {version}")

                try:
                    major_version = int(re.match(r"(\d+)", str(version)).group(1))
                except Exception as ex:
                    logger.warning(
                        f"Não foi possível detectar a versão major do MySQL: {version}. Erro: {ex}"
                    )
                    major_version = 8  # Assume 8 por segurança (não tenta query_cache)

                optimizations = []
                # query_cache_* só existe até MySQL 5.x
                if major_version < 8:
                    optimizations += [
                        "SET SESSION query_cache_type = ON",
                        "SET SESSION query_cache_size = 67108864",
                    ]
                # Otimizações que funcionam em todas as versões
                optimizations += [
                    "SET SESSION innodb_stats_on_metadata = 0",
                    "SET SESSION transaction_isolation = 'READ-COMMITTED'"
                ]
                
                # Aplica otimizações
                for query in optimizations:
                    try:
                        db.session.execute(text(query))
                    except Exception as e:
                        logger.warning(f"Otimização não aplicada: {query} - {e}")
                db.session.commit()
                logger.info("Otimizações de banco de dados aplicadas")
            
            elif "sqlite" in backend:
                # Otimizações para SQLite
                optimizations = [
                    "PRAGMA journal_mode = WAL",
                    "PRAGMA synchronous = NORMAL",
                    "PRAGMA temp_store = MEMORY",
                    "PRAGMA mmap_size = 30000000000",
                    "PRAGMA cache_size = -4000"  # ~4MB
                ]
                for query in optimizations:
                    try:
                        db.session.execute(text(query))
                    except Exception as e:
                        logger.warning(f"Otimização SQLite não aplicada: {query} - {e}")
                logger.info("Otimizações SQLite aplicadas")
            
            else:
                logger.info(f"Otimizações SQL ignoradas: backend em uso é '{backend}'")
                
            return True
            
        except Exception as e:
            logger.error(f"Erro ao aplicar otimizações de banco: {e}")
            db.session.rollback()
            return False

    @staticmethod
    def create_indexes() -> Dict[str, int]:
        """
        Cria índices para melhorar performance das consultas
        
        Returns:
            Dict[str, int]: Contagem de índices criados e ignorados
        """
        results = {"created": 0, "existing": 0, "failed": 0}
        
        try:
            # Detectar se estamos usando MySQL
            engine = db.get_engine()
            backend = engine.url.get_backend_name()
            is_mysql = "mysql" in backend
            
            # Ajustar sintaxe baseada no backend
            if_not_exists = "" if is_mysql else "IF NOT EXISTS "
            
            # Índices básicos para as tabelas principais
            indexes = [
                # Índices para tabela de endividamentos
                f"CREATE INDEX {if_not_exists}idx_endividamento_data_vencimento ON endividamento(data_vencimento_final)",
                f"CREATE INDEX {if_not_exists}idx_endividamento_banco ON endividamento(banco)",
                f"CREATE INDEX {if_not_exists}idx_endividamento_created_at ON endividamento(created_at)",
                
                # Índices para tabela de parcelas
                f"CREATE INDEX {if_not_exists}idx_parcela_data_vencimento ON parcela(data_vencimento)",
                f"CREATE INDEX {if_not_exists}idx_parcela_pago ON parcela(pago)",
                f"CREATE INDEX {if_not_exists}idx_parcela_endividamento_id ON parcela(endividamento_id)",
                
                # Índices para tabela de pessoas
                f"CREATE INDEX {if_not_exists}idx_pessoa_nome ON pessoa(nome)",
                f"CREATE INDEX {if_not_exists}idx_pessoa_cpf_cnpj ON pessoa(cpf_cnpj)",
                
                # Índices para tabela de documentos
                f"CREATE INDEX {if_not_exists}idx_documento_data_vencimento ON documento(data_vencimento)",
                f"CREATE INDEX {if_not_exists}idx_documento_tipo ON documento(tipo)",
                f"CREATE INDEX {if_not_exists}idx_documento_processamento ON documento(status_processamento)",
                
                # Índices para notificações
                f"CREATE INDEX {if_not_exists}idx_notificacao_endividamento_ativo ON notificacao_endividamento(ativo)",
                f"CREATE INDEX {if_not_exists}idx_notificacao_endividamento_enviado ON notificacao_endividamento(enviado)",
                f"CREATE INDEX {if_not_exists}idx_notificacao_endividamento_tipo ON notificacao_endividamento(tipo_notificacao)",
                f"CREATE INDEX {if_not_exists}idx_notificacao_endividamento_data_envio ON notificacao_endividamento(data_envio)",
                
                # Índices para histórico de notificações
                f"CREATE INDEX {if_not_exists}idx_historico_notificacao_data ON historico_notificacao(data_envio)",
                f"CREATE INDEX {if_not_exists}idx_historico_notificacao_endividamento ON historico_notificacao(endividamento_id)",
                f"CREATE INDEX {if_not_exists}idx_historico_notificacao_documento ON historico_notificacao_documento(documento_id)",
                
                # Índices compostos para otimizar consultas comuns
                f"CREATE INDEX {if_not_exists}idx_notificacao_pendente ON notificacao_endividamento(ativo, enviado, data_envio)",
                f"CREATE INDEX {if_not_exists}idx_documento_vencimento_status ON documento(data_vencimento, ativo)"
            ]
            
            # Para cada índice, tentar criar
            for index_query in indexes:
                try:
                    db.session.execute(text(index_query))
                    results["created"] += 1
                    logger.info(f"Índice criado: {index_query}")
                except Exception as e:
                    if "already exists" in str(e) or "Duplicate key name" in str(e):
                        results["existing"] += 1
                        logger.info(f"Índice já existe: {index_query}")
                    else:
                        results["failed"] += 1
                        logger.warning(f"Índice não criado: {index_query} - {e}")
                        
            db.session.commit()
            logger.info(f"Índices de performance: {results['created']} criados, {results['existing']} já existiam, {results['failed']} falhas")
            
            return results
            
        except Exception as e:
            logger.error(f"Erro ao criar índices: {e}")
            db.session.rollback()
            return {"created": 0, "existing": 0, "failed": 0, "error": str(e)}
            
    @staticmethod
    def analyze_slow_queries(threshold_seconds: float = 0.5) -> List[Dict[str, Any]]:
        """
        Analisa consultas lentas registradas
        
        Args:
            threshold_seconds: Limite em segundos para considerar uma consulta lenta
            
        Returns:
            Lista de consultas lentas com detalhes
        """
        slow_queries = performance_metrics.get("queries_lentas", [])
        return [query for query in slow_queries 
                if query.get("duration", 0) >= threshold_seconds]
    
    @staticmethod
    def get_database_metrics() -> Dict[str, Any]:
        """
        Obtém métricas sobre o banco de dados
        
        Returns:
            Métricas do banco de dados
        """
        try:
            metrics = {}
            engine = db.get_engine()
            backend = engine.url.get_backend_name()
            
            # Métricas básicas - contagem de registros por tabela
            table_counts = {}
            for table in ["documento", "endividamento", "notificacao_endividamento", 
                         "historico_notificacao", "pessoa", "fazenda"]:
                try:
                    count = db.session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                    table_counts[table] = count
                except:
                    table_counts[table] = "N/A"
            
            metrics["table_counts"] = table_counts
            
            # Métricas específicas por tipo de banco
            if "sqlite" in backend:
                # SQLite métricas
                try:
                    pragma_stats = {}
                    for pragma in ["page_count", "page_size", "freelist_count", "auto_vacuum"]:
                        pragma_stats[pragma] = db.session.execute(text(f"PRAGMA {pragma}")).scalar()
                    
                    # Calcular tamanho do banco
                    if "page_count" in pragma_stats and "page_size" in pragma_stats:
                        size_bytes = pragma_stats["page_count"] * pragma_stats["page_size"]
                        pragma_stats["db_size_mb"] = round(size_bytes / (1024 * 1024), 2)
                    
                    metrics["sqlite_stats"] = pragma_stats
                except Exception as e:
                    logger.error(f"Erro ao obter métricas SQLite: {e}")
            
            elif "mysql" in backend:
                # MySQL métricas
                try:
                    status = db.session.execute(text("SHOW STATUS")).fetchall()
                    metrics["mysql_stats"] = {row[0]: row[1] for row in status if row[0] in 
                                             ["Threads_connected", "Queries", "Slow_queries", 
                                              "Uptime", "Com_select", "Com_insert", "Com_update", "Com_delete"]}
                except Exception as e:
                    logger.error(f"Erro ao obter métricas MySQL: {e}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Erro ao obter métricas do banco: {e}")
            return {"error": str(e)}


def rate_limit(max_requests=100, window=3600):
    """Decorator para rate limiting"""


    def decorator(f):
        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            client_ip = request.environ.get("HTTP_X_FORWARDED_FOR", request.remote_addr)
            cache_key = f"rate_limit:{client_ip}:{f.__name__}"
            current_requests = cache.get(cache_key) or 0
            
            if current_requests >= max_requests:
                logger.warning(f"Rate limit excedido para {client_ip} em {f.__name__}")
                return (
                    jsonify({
                        "error": "Rate limit exceeded",
                        "message": f"Máximo de {max_requests} requisições por {window} segundos",
                        "retry_after": window
                    }),
                    429,
                    {"Retry-After": str(window)}
                )
                
            cache.set(cache_key, current_requests + 1, window)
            return f(*args, **kwargs)
            
        return wrapper  # type: ignore
        
    return decorator


def measure_performance(name: Optional[str] = None, threshold: float = 1.0) -> Callable:
    """
    Decorator para medir performance de funções
    
    Args:
        name: Nome personalizado para a função (opcional)
        threshold: Limite em segundos para considerar execução lenta
        
    Returns:
        Função decorada com medição de performance
    """
    def decorator(f: F) -> F:
        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            global performance_metrics
            func_name = name or f.__name__
            start_time = time.time()
            
            try:
                result = f(*args, **kwargs)
                
            finally:
                end_time = time.time()
                execution_time = end_time - start_time
                
                # Registrar métricas
                if func_name.startswith("enviar_") or "notificacao" in func_name.lower():
                    # Se for função de notificação, armazenar métricas específicas
                    if "notificacao_tempos" not in performance_metrics:
                        performance_metrics["notificacao_tempos"] = []
                    
                    performance_metrics["notificacao_tempos"].append(execution_time)
                    
                    # Atualizar média
                    tempos = performance_metrics["notificacao_tempos"]
                    performance_metrics["tempo_medio_envio_ms"] = sum(tempos) / len(tempos) * 1000
                
                # Log para funções lentas
                if execution_time > threshold:
                    logger.warning(
                        f"Função lenta: {func_name} - {execution_time:.2f}s "
                        f"(limite: {threshold:.2f}s)"
                    )
                    
                    # Adicionar à lista de funções lentas
                    if "funcoes_lentas" not in performance_metrics:
                        performance_metrics["funcoes_lentas"] = []
                        
                    performance_metrics["funcoes_lentas"].append({
                        "name": func_name,
                        "duration": execution_time,
                        "timestamp": datetime.now().isoformat(),
                        "threshold": threshold
                    })
            
            return result
            
        return wrapper  # type: ignore
        
    return decorator


@cached(timeout=1800, key_prefix="dashboard")
def get_dashboard_stats() -> Dict[str, Any]:
    """
    Obtém estatísticas do dashboard com cache
    
    Returns:
        Dicionário com estatísticas
    """
    try:
        from src.models.documento import Documento
        from src.models.endividamento import Endividamento
        from src.models.fazenda import Fazenda
        from src.models.pessoa import Pessoa
        from src.models.notificacao_endividamento import NotificacaoEndividamento

        hoje = date.today()
        stats = {
            "total_pessoas": Pessoa.query.count(),
            "total_fazendas": Fazenda.query.count(),
            "total_documentos": Documento.query.count(),
            "total_endividamentos": Endividamento.query.count(),
            "documentos_vencidos": Documento.query.filter(
                Documento.data_vencimento < hoje
            ).count(),
            "endividamentos_proximos": Endividamento.query.filter(
                Endividamento.data_vencimento_final.between(
                    hoje, hoje + timedelta(days=30)
                )
            ).count(),
            "notificacoes_pendentes": NotificacaoEndividamento.query.filter(
                NotificacaoEndividamento.ativo == True,
                NotificacaoEndividamento.enviado == False,
                NotificacaoEndividamento.data_envio <= datetime.utcnow()
            ).count()
        }
        return stats
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas do dashboard: {e}")
        return {}


@cached(timeout=3600, key_prefix="pessoas")
def get_pessoas_for_select() -> List[Dict[str, Any]]:
    """
    Obtém lista de pessoas para selects com cache
    
    Returns:
        Lista formatada de pessoas
    """
    try:
        from src.models.pessoa import Pessoa

        pessoas = (
            Pessoa.query.with_entities(Pessoa.id, Pessoa.nome, Pessoa.cpf_cnpj)
            .order_by(Pessoa.nome)
            .all()
        )
        return [{"id": p.id, "nome": p.nome, "cpf_cnpj": p.cpf_cnpj} for p in pessoas]
    except Exception as e:
        logger.error(f"Erro ao obter pessoas para select: {e}")
        return []


@cached(timeout=3600, key_prefix="fazendas")
def get_fazendas_for_select() -> List[Dict[str, Any]]:
    """
    Obtém lista de fazendas para selects com cache
    
    Returns:
        Lista formatada de fazendas
    """
    try:
        from src.models.fazenda import Fazenda

        fazendas = (
            Fazenda.query.with_entities(Fazenda.id, Fazenda.nome, Fazenda.tamanho_total)
            .order_by(Fazenda.nome)
            .all()
        )
        return [
            {"id": f.id, "nome": f.nome, "tamanho_total": float(f.tamanho_total)}
            for f in fazendas
        ]
    except Exception as e:
        logger.error(f"Erro ao obter fazendas para select: {e}")
        return []


def clear_related_cache(entity_type: str) -> int:
    """
    Limpa cache relacionado a uma entidade
    
    Args:
        entity_type: Tipo de entidade ('pessoa', 'fazenda', 'documento', 'endividamento')
        
    Returns:
        Número de entradas de cache limpas
    """
    patterns = {
        "pessoa": ["pessoas:*", "buscar_pessoas:*", "dashboard:*"],
        "fazenda": ["fazendas:*", "dashboard:*"],
        "documento": ["dashboard:*", "documentos:*", "vencimentos:*"],
        "endividamento": ["dashboard:*", "endividamentos:*", "vencimentos:*"],
        "notificacao": ["dashboard:*", "notificacoes:*"]
    }
    
    count = 0
    if entity_type in patterns:
        for pattern in patterns[entity_type]:
            try:
                count += cache.clear_pattern(pattern)
            except Exception as e:
                logger.warning(f"Erro ao limpar cache com pattern {pattern}: {e}")
    
    return count


class DatabaseOptimizer:
    """Otimizador de consultas ao banco de dados"""

    @staticmethod
    def optimize_endividamento_queries():
        """
        Otimiza consultas de endividamentos usando eager loading
        
        Returns:
            Query otimizada para endividamentos
        """
        from sqlalchemy.orm import joinedload
        from src.models.endividamento import Endividamento

        return Endividamento.query.options(
            joinedload(Endividamento.pessoas),
            joinedload(Endividamento.fazenda_vinculos),
            joinedload(Endividamento.parcelas),
        )

    @staticmethod
    def optimize_documento_queries():
        """
        Otimiza consultas de documentos usando eager loading
        
        Returns:
            Query otimizada para documentos
        """
        from sqlalchemy.orm import joinedload
        from src.models.documento import Documento

        return Documento.query.options(
            joinedload(Documento.pessoa),
            joinedload(Documento.fazenda),
        )
        
    @staticmethod
    def optimize_notificacoes_queries():
        """
        Otimiza consultas de notificações usando eager loading
        
        Returns:
            Query otimizada para notificações de endividamento
        """
        from sqlalchemy.orm import joinedload
        from src.models.notificacao_endividamento import NotificacaoEndividamento

        return NotificacaoEndividamento.query.options(
            joinedload(NotificacaoEndividamento.endividamento),
        )

    @staticmethod
    def get_vencimentos_otimizado(dias: int = 30) -> Dict[str, List[Any]]:
        """
        Obtém vencimentos de forma otimizada
        
        Args:
            dias: Número de dias para considerar no período
            
        Returns:
            Dicionário com parcelas e documentos
        """
        from sqlalchemy.orm import joinedload
        from src.models.documento import Documento
        from src.models.endividamento import Endividamento, Parcela

        hoje = date.today()
        data_limite = hoje + timedelta(days=dias)
        
        # Consulta otimizada de parcelas
        parcelas = (
            Parcela.query.options(
                joinedload(Parcela.endividamento).joinedload(Endividamento.pessoas)
            )
            .filter(
                Parcela.data_vencimento.between(hoje, data_limite),
                ~Parcela.pago,
            )
            .order_by(Parcela.data_vencimento)
            .all()
        )
        
        # Consulta otimizada de documentos
        documentos = (
            Documento.query.options(
                joinedload(Documento.pessoa),
                joinedload(Documento.fazenda),
            )
            .filter(
                Documento.data_vencimento.between(hoje, data_limite),
                Documento.ativo == True
            )
            .order_by(Documento.data_vencimento)
            .all()
        )
        
        return {"parcelas": parcelas, "documentos": documentos}
        
    @staticmethod
    def obter_notificacoes_pendentes(limite: int = 100) -> Dict[str, List[Any]]:
        """
        Obtém notificações pendentes de envio de forma otimizada
        
        Args:
            limite: Limite máximo de notificações a retornar
            
        Returns:
            Dicionário com notificações pendentes por tipo
        """
        from sqlalchemy.orm import joinedload
        from src.models.notificacao_endividamento import NotificacaoEndividamento
        
        # Consulta otimizada
        notificacoes = (
            NotificacaoEndividamento.query.options(
                joinedload(NotificacaoEndividamento.endividamento)
            )
            .filter(
                NotificacaoEndividamento.ativo == True,
                NotificacaoEndividamento.enviado == False,
                NotificacaoEndividamento.data_envio <= datetime.utcnow(),
                NotificacaoEndividamento.tentativas < 3,
                NotificacaoEndividamento.tipo_notificacao != 'config'
            )
            .order_by(
                NotificacaoEndividamento.data_envio
            )
            .limit(limite)
            .all()
        )
        
        # Agrupar por tipo
        resultado = {}
        for notif in notificacoes:
            tipo = notif.tipo_notificacao
            if tipo not in resultado:
                resultado[tipo] = []
            resultado[tipo].append(notif)
        
        return resultado


def compress_response(f: F) -> F:
    """
    Decorator para compressão de respostas
    
    Args:
        f: Função a ser decorada
        
    Returns:
        Função decorada
    """
    @wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        response = f(*args, **kwargs)
        
        if hasattr(response, "headers"):
            # Configurar cabeçalhos apropriados
            if request.endpoint and "static" in request.endpoint:
                # Para arquivos estáticos, usar cache de longo prazo
                response.headers["Cache-Control"] = "public, max-age=31536000"
            else:
                # Para conteúdo dinâmico, evitar cache
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
                
        return response
        
    return wrapper  # type: ignore


def track_notificacao_metrics(
    success: bool, 
    tipo: str, 
    duration: float
) -> None:
    """
    Registra métricas sobre o processamento de notificações
    
    Args:
        success: Se a notificação foi enviada com sucesso
        tipo: Tipo da notificação
        duration: Duração do processamento em segundos
    """
    global performance_metrics
    
    # Inicializar se necessário
    if "notificacoes_enviadas" not in performance_metrics:
        performance_metrics["notificacoes_enviadas"] = 0
    if "falhas_envio" not in performance_metrics:
        performance_metrics["falhas_envio"] = 0
    
    # Incrementar contador
    performance_metrics["notificacoes_enviadas"] += 1 if success else 0
    performance_metrics["falhas_envio"] += 0 if success else 1
    
    # Registrar tempo de processamento
    duration_ms = duration * 1000
    
    # Atualizar tempo médio com média móvel
    current_avg = performance_metrics.get("tempo_medio_envio_ms", 0)
    count = performance_metrics.get("notificacoes_enviadas", 0) + performance_metrics.get("falhas_envio", 0)
    
    if count > 1:
        # Média móvel ponderada (dá mais peso aos valores mais recentes)
        new_avg = (current_avg * 0.7) + (duration_ms * 0.3)
    else:
        new_avg = duration_ms
        
    performance_metrics["tempo_medio_envio_ms"] = new_avg
    
    # Registrar métricas específicas por tipo
    if "por_tipo" not in performance_metrics:
        performance_metrics["por_tipo"] = {}
        
    if tipo not in performance_metrics["por_tipo"]:
        performance_metrics["por_tipo"][tipo] = {
            "enviadas": 0,
            "falhas": 0,
            "tempo_medio_ms": 0
        }
        
    tipo_metrics = performance_metrics["por_tipo"][tipo]
    tipo_metrics["enviadas"] += 1 if success else 0
    tipo_metrics["falhas"] += 0 if success else 1
    
    # Atualizar tempo médio por tipo
    current_tipo_avg = tipo_metrics.get("tempo_medio_ms", 0)
    tipo_count = tipo_metrics["enviadas"] + tipo_metrics["falhas"]
    
    if tipo_count > 1:
        new_tipo_avg = (current_tipo_avg * 0.7) + (duration_ms * 0.3)
    else:
        new_tipo_avg = duration_ms
        
    tipo_metrics["tempo_medio_ms"] = new_tipo_avg


def get_performance_report() -> Dict[str, Any]:
    """
    Gera relatório completo de métricas de performance
    
    Returns:
        Dicionário com métricas de performance
    """
    global performance_metrics
    
    # Obter estatísticas do banco
    try:
        db_metrics = PerformanceOptimizer.get_database_metrics()
    except Exception as e:
        logger.error(f"Erro ao obter métricas do banco: {e}")
        db_metrics = {"error": str(e)}
    
    # Construir relatório
    report = {
        "timestamp": datetime.now().isoformat(),
        "notificacoes": {
            "enviadas": performance_metrics.get("notificacoes_enviadas", 0),
            "falhas": performance_metrics.get("falhas_envio", 0),
            "tempo_medio_ms": round(performance_metrics.get("tempo_medio_envio_ms", 0), 2),
            "por_tipo": performance_metrics.get("por_tipo", {})
        },
        "performance": {
            "funcoes_lentas": performance_metrics.get("funcoes_lentas", [])[-10:],  # Últimas 10
            "queries_lentas": performance_metrics.get("queries_lentas", [])[-10:]   # Últimas 10
        },
        "database": db_metrics
    }
    
    return report


def init_performance_optimizations(app: Any) -> Dict[str, Any]:
    """
    Inicializa todas as otimizações de performance
    
    Args:
        app: Aplicação Flask
        
    Returns:
        Resultado das otimizações aplicadas
    """
    result = {
        "cache_initialized": False,
        "indexes_created": 0,
        "db_optimized": False
    }
    
    try:
        # Inicializar cache
        from src.utils.cache import cache
        cache.init_app(app)
        result["cache_initialized"] = True
        
        # Aplicar otimizações dentro do contexto da aplicação
        with app.app_context():
            # Criar índices
            indexes = PerformanceOptimizer.create_indexes()
            result["indexes_created"] = indexes.get("created", 0)
            result["indexes_existing"] = indexes.get("existing", 0)
            
            # Otimizar consultas
            db_optimized = PerformanceOptimizer.optimize_database_queries()
            result["db_optimized"] = db_optimized
            
        app.logger.info("Otimizações de performance inicializadas com sucesso")
        
    except Exception as e:
        app.logger.error(f"Erro ao inicializar otimizações: {e}")
        result["error"] = str(e)
    
    return result


class PerformanceMiddleware:

    def __init__(self, app):
        self.app = app
        self.init_app(app)

    def init_app(self, app: Any) -> None:
        """
        Registra os handlers de requisição no app Flask
        
        Args:
            app: Aplicação Flask
        """
        app.before_request(self.before_request)
        app.after_request(self.after_request)

    def before_request(self) -> None:
        """Registra o início da requisição"""
        request.start_time = time.time()

    def after_request(self, response: Response) -> Response:
        """
        Processa métricas após a requisição
        
        Args:
            response: Resposta HTTP
            
        Returns:
            Resposta HTTP inalterada
        """
        if hasattr(request, "start_time"):
            duration = time.time() - request.start_time
            
            # Registrar métricas para requisições lentas
            if duration > 1.0:
                endpoint = request.endpoint or "unknown"
                
                # Adicionar cabeçalho com tempo de resposta
                response.headers["X-Response-Time"] = f"{duration:.3f}s"
                
                # Requisições muito lentas geram alerta
                if duration > 2.0:
                    current_app.logger.warning(
                        f"Requisição lenta: {request.method} {request.path} - {duration:.2f}s"
                    )
                    
                    # Armazenar métricas detalhadas para requisições muito lentas
                    global performance_metrics
                    if "requests" not in performance_metrics:
                        performance_metrics["requests"] = {}
                    
                    if endpoint not in performance_metrics["requests"]:
                        performance_metrics["requests"][endpoint] = {
                            "count": 0, 
                            "total_time": 0, 
                            "max_time": 0
                        }
                    
                    metrics = performance_metrics["requests"][endpoint]
                    metrics["count"] += 1
                    metrics["total_time"] += duration
                    metrics["max_time"] = max(metrics["max_time"], duration)
                    metrics["avg_time"] = metrics["total_time"] / metrics["count"]
        
        return response
