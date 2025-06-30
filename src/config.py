# /src/config.py

"""
Configuração centralizada para o sistema de Gestão Agro.
Utilize variáveis de ambiente para definir valores sensíveis e específicos de cada ambiente.

Exemplo de uso:
    from src.config import config_by_name
    app.config.from_object(config_by_name[os.getenv("FLASK_ENV", "development")])
"""

import os

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

    # Celery (tarefas assíncronas, se usar)
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

    # Outras configs centralizadas (exemplo, adicione o que precisar)
    # LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    # CACHE_TIMEOUT = int(os.getenv("CACHE_TIMEOUT", 300))


class DevelopmentConfig(Config):
    """Configurações para ambiente de desenvolvimento."""

    DEBUG = True


class TestingConfig(Config):
    """Configurações para ambiente de testes."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class ProductionConfig(Config):
    """Configurações para produção."""

    DEBUG = False


config_by_name = dict(
    development=DevelopmentConfig,
    testing=TestingConfig,
    production=ProductionConfig,
)
