# /src/routes/__init__.py

from .admin import admin_bp
from .endividamento import endividamento_bp
from .fazenda import fazenda_bp  # Registra o blueprint de API de fazenda


def register_blueprints(app):
    """Registra todos os blueprints das rotas principais do sistema."""
    app.register_blueprint(admin_bp)
    app.register_blueprint(endividamento_bp)
    app.register_blueprint(fazenda_bp)  # Se você tem rotas REST para fazenda

# Se você criar um blueprint separado para rotas admin HTML de fazenda (ex: fazenda_admin_bp),
# também deve importar e registrar aqui.

# Exemplo:
# from .fazenda_admin import fazenda_admin_bp
# ...
#     app.register_blueprint(fazenda_admin_bp)
