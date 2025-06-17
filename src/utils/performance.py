#/src/utils/performance.py

from functools import wraps
import time
import logging
import re

from flask import request, jsonify, current_app
from sqlalchemy import text
from src.models.db import db
from src.utils.cache import cache, cached

logger = logging.getLogger(__name__)

class PerformanceOptimizer:
    """Classe para otimizações de performance"""

    @staticmethod
    def optimize_database_queries():
        """Otimiza configurações do banco de dados"""
        try:
            engine = db.get_engine()
            backend = engine.url.get_backend_name()
            logger.info(f"Backend do banco detectado: {backend}")
            if 'mysql' in backend:
                # Detecta versão do MySQL
                version = db.session.execute(text("SELECT VERSION()")).scalar()
                logger.info(f"MySQL version detected: {version}")

                try:
                    major_version = int(re.match(r"(\d+)", version).group(1))
                except Exception as ex:
                    logger.warning(f"Não foi possível detectar a versão major do MySQL: {version}. Erro: {ex}")
                    major_version = 8  # Assume 8 por segurança (não tenta query_cache)

                optimizations = []
                # query_cache_* só existe até MySQL 5.x
                if major_version < 8:
                    optimizations += [
                        "SET SESSION query_cache_type = ON",
                        "SET SESSION query_cache_size = 67108864"
                    ]
                # Não tente setar innodb_buffer_pool_size como SESSION nem se for MySQL 8
                # Em ambientes gerenciados, nem tente setar GLOBAL.
                for query in optimizations:
                    try:
                        db.session.execute(text(query))
                    except Exception as e:
                        logger.warning(f"Otimização não aplicada: {query} - {e}")
                db.session.commit()
                logger.info("Otimizações de banco de dados aplicadas")
            else:
                logger.info(f"Otimizações SQL ignoradas: backend em uso é '{backend}'")
        except Exception as e:
            logger.error(f"Erro ao aplicar otimizações de banco: {e}")
            db.session.rollback()

    @staticmethod
    def create_indexes():
        """Cria índices para melhorar performance das consultas"""
        try:
            indexes = [
                # Índices para tabela de endividamentos
                "CREATE INDEX idx_endividamento_data_vencimento ON endividamento(data_vencimento_final)",
                "CREATE INDEX idx_endividamento_banco ON endividamento(banco)",
                "CREATE INDEX idx_endividamento_created_at ON endividamento(created_at)",
                # Índices para tabela de parcelas
                "CREATE INDEX idx_parcela_data_vencimento ON parcela(data_vencimento)",
                "CREATE INDEX idx_parcela_pago ON parcela(pago)",
                "CREATE INDEX idx_parcela_endividamento_id ON parcela(endividamento_id)",
                # Índices para tabela de pessoas
                "CREATE INDEX idx_pessoa_nome ON pessoa(nome)",
                "CREATE INDEX idx_pessoa_cpf_cnpj ON pessoa(cpf_cnpj)",
                # Índices para tabela de documentos
                "CREATE INDEX idx_documento_data_vencimento ON documento(data_vencimento)",
                "CREATE INDEX idx_documento_tipo ON documento(tipo)",
                # Índices para notificações
                "CREATE INDEX idx_notificacao_endividamento_ativo ON notificacao_endividamento(ativo)",
                "CREATE INDEX idx_historico_notificacao_data ON historico_notificacao(data_envio)",
            ]
            for index_query in indexes:
                try:
                    db.session.execute(text(index_query))
                    logger.info(f"Índice criado: {index_query}")
                except Exception as e:
                    if "Duplicate key name" in str(e):
                        logger.info(f"Índice já existe: {index_query}")
                    else:
                        logger.warning(f"Índice não criado: {index_query} - {e}")
            db.session.commit()
            logger.info("Índices de performance criados com sucesso")
        except Exception as e:
            logger.error(f"Erro ao criar índices: {e}")
            db.session.rollback()

def rate_limit(max_requests=100, window=3600):
    """Decorator para rate limiting"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            cache_key = f"rate_limit:{client_ip}:{f.__name__}"
            current_requests = cache.get(cache_key) or 0
            if current_requests >= max_requests:
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Máximo de {max_requests} requisições por hora'
                }), 429
            cache.set(cache_key, current_requests + 1, window)
            return f(*args, **kwargs)
        return wrapper
    return decorator

def measure_performance(f):
    """Decorator para medir performance de funções"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = f(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        if execution_time > 1.0:
            logger.warning(f"Função {f.__name__} demorou {execution_time:.2f}s para executar")
        return result
    return wrapper

@cached(timeout=1800, key_prefix='dashboard')
def get_dashboard_stats():
    """Obtém estatísticas do dashboard com cache"""
    try:
        from src.models.pessoa import Pessoa
        from src.models.fazenda import Fazenda
        from src.models.documento import Documento
        from src.models.endividamento import Endividamento
        from datetime import date, timedelta
        hoje = date.today()
        stats = {
            'total_pessoas': Pessoa.query.count(),
            'total_fazendas': Fazenda.query.count(),
            'total_documentos': Documento.query.count(),
            'total_endividamentos': Endividamento.query.count(),
            'documentos_vencidos': Documento.query.filter(Documento.data_vencimento < hoje).count(),
            'endividamentos_proximos': Endividamento.query.filter(
                Endividamento.data_vencimento_final.between(hoje, hoje + timedelta(days=30))
            ).count()
        }
        return stats
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas do dashboard: {e}")
        return {}

@cached(timeout=3600, key_prefix='pessoas')
def get_pessoas_for_select():
    """Obtém lista de pessoas para selects com cache"""
    try:
        from src.models.pessoa import Pessoa
        pessoas = Pessoa.query.with_entities(
            Pessoa.id, 
            Pessoa.nome, 
            Pessoa.cpf_cnpj
        ).order_by(Pessoa.nome).all()
        return [{'id': p.id, 'nome': p.nome, 'cpf_cnpj': p.cpf_cnpj} for p in pessoas]
    except Exception as e:
        logger.error(f"Erro ao obter pessoas para select: {e}")
        return []

@cached(timeout=3600, key_prefix='fazendas')
def get_fazendas_for_select():
    """Obtém lista de fazendas para selects com cache"""
    try:
        from src.models.fazenda import Fazenda
        fazendas = Fazenda.query.with_entities(
            Fazenda.id, 
            Fazenda.nome, 
            Fazenda.tamanho_total
        ).order_by(Fazenda.nome).all()
        return [{'id': f.id, 'nome': f.nome, 'tamanho_total': float(f.tamanho_total)} for f in fazendas]
    except Exception as e:
        logger.error(f"Erro ao obter fazendas para select: {e}")
        return []

def clear_related_cache(entity_type):
    """Limpa cache relacionado a uma entidade"""
    patterns = {
        'pessoa': ['pessoas:*', 'dashboard:*'],
        'fazenda': ['fazendas:*', 'dashboard:*'],
        'documento': ['dashboard:*'],
        'endividamento': ['dashboard:*']
    }
    if entity_type in patterns:
        for pattern in patterns[entity_type]:
            cache.clear_pattern(pattern)

class DatabaseOptimizer:
    """Otimizador de consultas ao banco de dados"""

    @staticmethod
    def optimize_endividamento_queries():
        """Otimiza consultas de endividamentos usando eager loading"""
        from src.models.endividamento import Endividamento
        from sqlalchemy.orm import joinedload
        return Endividamento.query.options(
            joinedload(Endividamento.pessoas),
            joinedload(Endividamento.fazenda_vinculos),
            joinedload(Endividamento.parcelas)
        )

    @staticmethod
    def optimize_documento_queries():
        """Otimiza consultas de documentos usando eager loading"""
        from src.models.documento import Documento
        from sqlalchemy.orm import joinedload
        return Documento.query.options(
            joinedload(Documento.pessoa),
            joinedload(Documento.fazenda),
            joinedload(Documento.tipo_documento)
        )

    @staticmethod
    def get_vencimentos_otimizado(dias=30):
        """Obtém vencimentos de forma otimizada"""
        from src.models.endividamento import Endividamento, Parcela
        from src.models.documento import Documento
        from datetime import date, timedelta
        from sqlalchemy.orm import joinedload
        hoje = date.today()
        data_limite = hoje + timedelta(days=dias)
        parcelas = Parcela.query.options(
            joinedload(Parcela.endividamento).joinedload(Endividamento.pessoas)
        ).filter(
            Parcela.data_vencimento.between(hoje, data_limite),
            Parcela.pago == False
        ).order_by(Parcela.data_vencimento).all()
        documentos = Documento.query.options(
            joinedload(Documento.pessoa),
            joinedload(Documento.fazenda),
            joinedload(Documento.tipo_documento)
        ).filter(
            Documento.data_vencimento.between(hoje, data_limite)
        ).order_by(Documento.data_vencimento).all()
        return {
            'parcelas': parcelas,
            'documentos': documentos
        }

def compress_response(f):
    """Decorator para compressão de respostas"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        response = f(*args, **kwargs)
        if hasattr(response, 'headers'):
            if request.endpoint and 'static' in request.endpoint:
                response.headers['Cache-Control'] = 'public, max-age=31536000'
            else:
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
        return response
    return wrapper

def init_performance_optimizations(app):
    """Inicializa todas as otimizações de performance"""
    try:
        from src.utils.cache import cache
        cache.init_app(app)
        with app.app_context():
            optimizer = PerformanceOptimizer()
            optimizer.create_indexes()
            optimizer.optimize_database_queries()
        app.logger.info("Otimizações de performance inicializadas com sucesso")
    except Exception as e:
        app.logger.error(f"Erro ao inicializar otimizações: {e}")

class PerformanceMiddleware:
    def __init__(self, app):
        self.app = app
        self.init_app(app)

    def init_app(self, app):
        app.before_request(self.before_request)
        app.after_request(self.after_request)

    def before_request(self):
        request.start_time = time.time()

    def after_request(self, response):
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            if duration > 2.0:
                current_app.logger.warning(
                    f"Requisição lenta: {request.method} {request.path} - {duration:.2f}s"
                )
        return response
    