# /src/config.py

"""
Configuração centralizada para o sistema de Gestão Agro.
Utilize variáveis de ambiente para definir valores sensíveis e específicos de cada ambiente.

Exemplo de uso:
    from src.config import config_by_name
    app.config.from_object(config_by_name[os.getenv("FLASK_ENV", "development")])
"""

import os
from datetime import timedelta
from celery.schedules import crontab
from typing import Any, Optional

# Timezone padrão do sistema
CELERY_TIMEZONE = "America/Sao_Paulo"
DEFAULT_TIMEZONE = "America/Sao_Paulo"


def str_to_bool(value: Optional[str], default: bool = False) -> bool:
    """Converte string de ambiente para booleano."""
    if value is None:
        return default
    return str(value).strip().lower() in ("true", "1", "yes", "on", "sim")


def parse_int_env(var: str, default: int) -> int:
    """
    Tenta converter a variável de ambiente para inteiro, ignorando comentários após o valor.
    Exemplo: '16777216  # 16MB' -> 16777216
    """
    val = os.getenv(var)
    if val is None:
        return default
    try:
        # Pega apenas a primeira parte antes de qualquer espaço (para ignorar comentários)
        return int(val.split()[0])
    except (ValueError, IndexError):
        return default


def parse_str_env(var: str, default: str) -> str:
    """
    Pega a variável de ambiente como string, ignorando comentários após o valor.
    Exemplo: 'development  # produção' -> 'development'
    """
    val = os.getenv(var)
    if val is None:
        return default
    return val.split("#")[0].strip()


def parse_list_env(var: str, default: list, separator: str = ',') -> list:
    """
    Converte uma variável de ambiente em lista.
    Exemplo: 'email1@test.com,email2@test.com' -> ['email1@test.com', 'email2@test.com']
    """
    val = os.getenv(var)
    if val is None:
        return default
    return [item.strip() for item in val.split(separator) if item.strip()]


class Config:
    """
    Configuração base. Não utilize diretamente, use uma das subclasses.
    """

    # ========== SEGURANÇA ==========
    SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(24).hex())
    WTF_CSRF_ENABLED = str_to_bool(os.getenv("WTF_CSRF_ENABLED", "true"))
    WTF_CSRF_TIME_LIMIT = parse_int_env("WTF_CSRF_TIME_LIMIT", 3600)  # 1 hora

    # ========== BANCO DE DADOS ==========
    # Prioriza DATABASE_URL (formato Railway/Heroku), senão monta usando variáveis separadas
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL") or (
        f"mysql+pymysql://{os.getenv('DB_USERNAME', 'root')}:"
        f"{os.getenv('DB_PASSWORD', '1234')}@"
        f"{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '3306')}/"
        f"{os.getenv('DB_NAME', 'gestao_fazendas')}"
        f"?charset=utf8mb4"
        if os.getenv("DB_TYPE", "sqlite") == "mysql"
        else f"sqlite:///{os.path.join(os.path.dirname(__file__), '..', 'data.db')}"
    )
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 3600,  # Recicla conexões a cada hora
        'pool_size': 10,
        'max_overflow': 20,
        'echo': str_to_bool(os.getenv("SQLALCHEMY_ECHO", "false"))
    }

    # ========== E-MAIL ==========
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = parse_int_env("MAIL_PORT", 587)
    MAIL_USE_TLS = str_to_bool(os.getenv("MAIL_USE_TLS", "true"))
    MAIL_USE_SSL = str_to_bool(os.getenv("MAIL_USE_SSL", "false"))
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "noreply@gestaoagro.com")
    MAIL_MAX_EMAILS = parse_int_env("MAIL_MAX_EMAILS", 100)  # Limite de emails por conexão
    MAIL_ASCII_ATTACHMENTS = False
    MAIL_TIMEOUT = parse_int_env("MAIL_TIMEOUT", 30)  # Timeout de conexão

    # ========== REDIS/CACHE ==========
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_DECODE_RESPONSES = True
    REDIS_SOCKET_TIMEOUT = parse_int_env("REDIS_SOCKET_TIMEOUT", 5)
    REDIS_CONNECTION_POOL_KWARGS = {
        'max_connections': parse_int_env("REDIS_MAX_CONNECTIONS", 50),
        'retry_on_timeout': True,
        'socket_keepalive': True,
        'socket_keepalive_options': {}
    }

    # ========== UPLOADS ==========
    UPLOAD_FOLDER = os.getenv(
        "UPLOAD_FOLDER",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads")),
    )
    MAX_CONTENT_LENGTH = parse_int_env("MAX_CONTENT_LENGTH", 16 * 1024 * 1024)  # 16MB
    ALLOWED_EXTENSIONS = parse_list_env(
        "ALLOWED_EXTENSIONS",
        ['pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx']
    )

    # ========== CONFIGURAÇÕES DO CELERY (CRÍTICO PARA NOTIFICAÇÕES) ==========

    # URLs do Celery
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

    # Configurações essenciais do Celery
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_TIMEZONE = CELERY_TIMEZONE
    CELERY_ENABLE_UTC = True

    # Configuração de expiração de resultados
    CELERY_RESULT_EXPIRES = 3600  # 1 hora

    # Configuração de retry
    CELERY_TASK_SOFT_TIME_LIMIT = 300  # 5 minutos
    CELERY_TASK_TIME_LIMIT = 600  # 10 minutos
    CELERY_TASK_MAX_RETRIES = 3
    CELERY_TASK_DEFAULT_RETRY_DELAY = 60  # 1 minuto

    # ========== AGENDAMENTO DE TAREFAS (CELERY BEAT) ==========
    CELERY_BEAT_SCHEDULE = {
        # Verifica notificações a cada 5 minutos
        'verificar-notificacoes-periodicamente': {
            'task': 'tasks.processar_todas_notificacoes',
            'schedule': timedelta(minutes=5),
            'options': {
                'expires': 300,  # Expira em 5 minutos se não executar
                'priority': 5,
            }
        },

        # Verificação diária às 8h da manhã (horário de Brasília)
        'verificacao-matinal-notificacoes': {
            'task': 'tasks.processar_todas_notificacoes',
            'schedule': crontab(hour=8, minute=0),
            'options': {
                'expires': 3600,  # Expira em 1 hora se não executar
                'priority': 10,
            }
        },

        # Verificação adicional às 14h
        'verificacao-vespertina-notificacoes': {
            'task': 'tasks.processar_todas_notificacoes',
            'schedule': crontab(hour=14, minute=0),
            'options': {
                'expires': 3600,
                'priority': 10,
            }
        },
        
        # Verificação noturna às 20h (último aviso do dia)
        'verificacao-noturna-notificacoes': {
            'task': 'tasks.processar_todas_notificacoes',
            'schedule': crontab(hour=20, minute=0),
            'options': {
                'expires': 3600,
                'priority': 10,
            }
        },

        # Limpeza de notificações antigas (diariamente às 2h da manhã)
        'limpar-notificacoes-antigas': {
            'task': 'tasks.limpar_notificacoes_antigas',
            'schedule': crontab(hour=2, minute=0),
            'kwargs': {'dias': 90},  # Limpar notificações com mais de 90 dias
            'options': {
                'expires': 3600,
                'priority': 1,
            }
        },
        
        # Health check do sistema (a cada 10 minutos)
        'health-check-celery': {
            'task': 'tasks.test_celery',
            'schedule': timedelta(minutes=10),
            'options': {
                'expires': 600,
                'priority': 1,
            }
        },
    }

    # ========== CONFIGURAÇÕES DE NOTIFICAÇÃO ==========
    NOTIFICATION_CHECK_INTERVAL = parse_int_env("NOTIFICATION_CHECK_INTERVAL", 300)  # 5 minutos
    NOTIFICATION_DAYS_BEFORE = parse_list_env(
        "NOTIFICATION_DAYS_BEFORE", 
        [180, 90, 60, 30, 15, 7, 3, 1]
    )
    NOTIFICATION_EMAIL_ENABLED = str_to_bool(os.getenv("NOTIFICATION_EMAIL_ENABLED", "true"))

    # ========== LOGGING ==========
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_TO_STDOUT = str_to_bool(os.getenv("LOG_TO_STDOUT", "false"))

    # ========== CACHE ==========
    CACHE_TYPE = os.getenv("CACHE_TYPE", "RedisCache")
    CACHE_REDIS_URL = os.getenv("CACHE_REDIS_URL", REDIS_URL)
    CACHE_DEFAULT_TIMEOUT = parse_int_env("CACHE_DEFAULT_TIMEOUT", 300)
    CACHE_KEY_PREFIX = os.getenv("CACHE_KEY_PREFIX", "gestao_agro_")
    
    # ========== SESSÃO ==========
    SESSION_TYPE = 'redis'
    SESSION_REDIS = REDIS_URL
    SESSION_PERMANENT = False
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_NAME = 'gestao_agro_session'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # ========== APLICAÇÃO ==========
    APP_NAME = os.getenv("APP_NAME", "Gestão Agro")
    APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
    APP_DESCRIPTION = os.getenv("APP_DESCRIPTION", "Sistema de Gestão Agrícola")
    
    # ========== RATE LIMITING ==========
    RATELIMIT_ENABLED = str_to_bool(os.getenv("RATELIMIT_ENABLED", "true"))
    RATELIMIT_STORAGE_URL = os.getenv("RATELIMIT_STORAGE_URL", REDIS_URL)
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "200 per day, 50 per hour")
    RATELIMIT_HEADERS_ENABLED = True


class DevelopmentConfig(Config):
    """Configurações para ambiente de desenvolvimento."""
    DEBUG = True

    # Em desenvolvimento, verificar notificações mais frequentemente
    CELERY_BEAT_SCHEDULE = {
        **Config.CELERY_BEAT_SCHEDULE,
        'verificar-notificacoes-dev': {
            'task': 'tasks.processar_todas_notificacoes',
            'schedule': timedelta(minutes=1),  # A cada minuto em dev
            'options': {
                'expires': 60,
                'priority': 10,
            }
        },
    }
    
    # Logs mais verbosos em desenvolvimento
    LOG_LEVEL = "DEBUG"
    SQLALCHEMY_ECHO = True
    
    # Desabilitar algumas seguranças para facilitar desenvolvimento
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False


class TestingConfig(Config):
    """Configurações para ambiente de testes."""
    TESTING = True
    DEBUG = True
    
    # Banco de dados em memória para testes
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    
    # Celery síncrono para testes
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    
    # Desabilitar CSRF para testes
    WTF_CSRF_ENABLED = False
    
    # Cache simples para testes
    CACHE_TYPE = "SimpleCache"
    
    # Desabilitar rate limiting em testes
    RATELIMIT_ENABLED = False


class ProductionConfig(Config):
    """Configurações para produção."""
    DEBUG = False

    # Em produção, garantir que logs sejam mais detalhados
    LOG_LEVEL = os.getenv("LOG_LEVEL", "WARNING")

    # Forçar HTTPS em produção
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Configurações específicas do Railway
    if os.getenv("RAILWAY_ENVIRONMENT"):
        # Railway fornece PORT automaticamente
        PORT = int(os.getenv("PORT", 5000))

        # Ajustar Redis URL se fornecido pelo Railway
        if os.getenv("REDIS_URL"):
            REDIS_URL = os.getenv("REDIS_URL")
            CELERY_BROKER_URL = REDIS_URL
            CELERY_RESULT_BACKEND = REDIS_URL
            CACHE_REDIS_URL = REDIS_URL
            SESSION_REDIS = REDIS_URL
            RATELIMIT_STORAGE_URL = REDIS_URL
        
        # Log para stdout no Railway
        LOG_TO_STDOUT = True
    
    # Configurações específicas do Heroku
    if os.getenv("DYNO"):
        LOG_TO_STDOUT = True
        
        # Ajustar database URL do Heroku (postgres:// -> postgresql://)
        db_url = os.getenv("DATABASE_URL")
        if db_url and db_url.startswith("postgres://"):
            SQLALCHEMY_DATABASE_URI = db_url.replace("postgres://", "postgresql://", 1)


config_by_name = dict(
    development=DevelopmentConfig,
    testing=TestingConfig,
    production=ProductionConfig,
)
