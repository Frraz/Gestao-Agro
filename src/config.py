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

CELERY_TIMEZONE = "America/Sao_Paulo"


def str_to_bool(value, default=False):
    """Converte string de ambiente para booleano."""
    if value is None:
        return default
    return str(value).strip().lower() in ("true", "1", "yes", "on")


def parse_int_env(var, default):
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
    except Exception:
        return default


def parse_str_env(var, default):
    """
    Pega a variável de ambiente como string, ignorando comentários após o valor.
    Exemplo: 'development  # produção' -> 'development'
    """
    val = os.getenv(var)
    if val is None:
        return default
    return val.split("#")[0].strip()


class Config:
    """
    Configuração base. Não utilize diretamente, use uma das subclasses.
    """

    # Segurança
    SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(24))

    # Banco de dados (prioriza DATABASE_URL, senão monta usando variáveis separadas)
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL") or (
        f"mysql+pymysql://{os.getenv('DB_USERNAME', 'root')}:"
        f"{os.getenv('DB_PASSWORD', '1234')}@"
        f"{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '3306')}/"
        f"{os.getenv('DB_NAME', 'gestao_fazendas')}"
        if os.getenv("DB_TYPE", "sqlite") == "mysql"
        else "sqlite:///data.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # E-mail
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS = str_to_bool(os.getenv("MAIL_USE_TLS", "true"))
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "admin@example.com")

    # Redis/Cache
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Uploads
    UPLOAD_FOLDER = os.getenv(
        "UPLOAD_FOLDER",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads")),
    )
    MAX_CONTENT_LENGTH = parse_int_env("MAX_CONTENT_LENGTH", 16 * 1024 * 1024)

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
            }
        },
        
        # Verificação diária às 8h da manhã (horário de Brasília)
        'verificacao-matinal-notificacoes': {
            'task': 'tasks.processar_todas_notificacoes',
            'schedule': crontab(hour=8, minute=0),
            'options': {
                'expires': 3600,  # Expira em 1 hora se não executar
            }
        },
        
        # Verificação adicional às 14h
        'verificacao-vespertina-notificacoes': {
            'task': 'tasks.processar_todas_notificacoes',
            'schedule': crontab(hour=14, minute=0),
            'options': {
                'expires': 3600,
            }
        },
        
        # Limpeza de notificações antigas (diariamente às 2h da manhã)
        'limpar-notificacoes-antigas': {
            'task': 'tasks.limpar_notificacoes_antigas',
            'schedule': crontab(hour=2, minute=0),
            'options': {
                'expires': 3600,
            }
        },
    }
    
    # ========== CONFIGURAÇÕES DE NOTIFICAÇÃO ==========
    NOTIFICATION_CHECK_INTERVAL = int(os.getenv("NOTIFICATION_CHECK_INTERVAL", 300))  # 5 minutos
    NOTIFICATION_DAYS_BEFORE = int(os.getenv("NOTIFICATION_DAYS_BEFORE", 30))  # Avisar 30 dias antes
    NOTIFICATION_EMAIL_ENABLED = str_to_bool(os.getenv("NOTIFICATION_EMAIL_ENABLED", "true"))
    
    # ========== LOGGING ==========
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_TO_STDOUT = str_to_bool(os.getenv("LOG_TO_STDOUT", "false"))
    
    # ========== CACHE ==========
    CACHE_TYPE = os.getenv("CACHE_TYPE", "simple")
    CACHE_REDIS_URL = os.getenv("CACHE_REDIS_URL", REDIS_URL)
    CACHE_DEFAULT_TIMEOUT = int(os.getenv("CACHE_DEFAULT_TIMEOUT", 300))


class DevelopmentConfig(Config):
    """Configurações para ambiente de desenvolvimento."""
    DEBUG = True
    
    # Em desenvolvimento, verificar notificações mais frequentemente
    CELERY_BEAT_SCHEDULE = {
        **Config.CELERY_BEAT_SCHEDULE,
        'verificar-notificacoes-dev': {
            'task': 'tasks.processar_todas_notificacoes',
            'schedule': timedelta(minutes=1),  # A cada minuto em dev
        },
    }


class TestingConfig(Config):
    """Configurações para ambiente de testes."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    CELERY_TASK_ALWAYS_EAGER = True  # Executa tarefas sincronamente em testes
    CELERY_TASK_EAGER_PROPAGATES = True


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


config_by_name = dict(
    development=DevelopmentConfig,
    testing=TestingConfig,
    production=ProductionConfig,
)