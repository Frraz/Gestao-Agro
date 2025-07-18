# /src/main.py

import os
import sys
import datetime
import logging
import time

from logging.handlers import RotatingFileHandler

# Ajuste o sys.path ANTES dos imports locais do projeto:
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

os.environ["TZ"] = "America/Sao_Paulo"
try:
    time.tzset()  # Só funciona em Unix/Linux (como Railway)
except AttributeError:
    pass  # Ignora em sistemas onde tzset não está disponível

from dotenv import load_dotenv
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from flask_login import LoginManager
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

# Carrega variáveis de ambiente ANTES de outros imports
load_dotenv()

from src.models.db import db
from src.routes.admin import admin_bp
from src.routes.auditoria import auditoria_bp
from src.routes.auth import auth_bp
from src.routes.documento import documento_bp
from src.routes.endividamento import endividamento_bp
from src.routes.fazenda import fazenda_bp
from src.routes.pessoa import pessoa_bp
from src.routes.test import test_bp
from src.utils.filters import register_filters
from src.utils.performance import PerformanceMiddleware, init_performance_optimizations
from src.config import config_by_name, parse_str_env

# ========== IMPORTAÇÃO DO CELERY ==========
from src.utils.tasks import make_celery
from src.utils.tasks_notificacao import criar_tarefas_notificacao

# Variável global para o Celery
celery = None


def configure_logging(app):
    if not os.path.exists("logs"):
        os.mkdir("logs")
    file_handler = RotatingFileHandler(
        "logs/sistema_fazendas.log", maxBytes=10240, backupCount=10
    )
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
        )
    )
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info("Inicialização do Sistema de Gestão de Fazendas")
    return app


def allowed_file(filename):
    ALLOWED_EXTENSIONS = {
        "pdf",
        "png",
        "jpg",
        "jpeg",
        "gif",
        "doc",
        "docx",
        "xls",
        "xlsx",
    }
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def create_app(test_config=None):
    global celery
    
    app = Flask(__name__)

    # Configuração centralizada
    config_name = parse_str_env("FLASK_ENV", "development")
    app.config.from_object(config_by_name[config_name])
    
    # Garantir que REDIS_URL do ambiente (.env) está presente na config Flask
    if "REDIS_URL" not in app.config or not app.config["REDIS_URL"]:
        app.config["REDIS_URL"] = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    
    # Garantir que as configurações do Celery estão presentes
    app.config["CELERY_BROKER_URL"] = app.config.get("CELERY_BROKER_URL", app.config["REDIS_URL"])
    app.config["CELERY_RESULT_BACKEND"] = app.config.get("CELERY_RESULT_BACKEND", app.config["REDIS_URL"])

    if test_config:
        app.config.update(test_config)

    # Configurar logging ANTES de usar app.logger
    configure_logging(app)

    register_filters(app)

    # ========== INICIALIZAÇÃO DO CELERY ==========
    celery = make_celery(app)
    
    # Registrar tarefas de notificação
    criar_tarefas_notificacao(celery)
    
    # Registrar tasks dos serviços de notificação
    try:
        from src.utils.notificacao_documentos_service import criar_task_verificar_documentos
        from src.utils.notificacao_endividamento_service import criar_task_verificar_endividamentos
        
        criar_task_verificar_documentos(celery)
        criar_task_verificar_endividamentos(celery)
    except Exception as e:
        app.logger.warning(f"Erro ao registrar tasks de serviços: {e}")
    
    # Log de confirmação
    app.logger.info(f"Celery inicializado com broker: {app.config.get('CELERY_BROKER_URL')}")

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    from src.models.usuario import Usuario

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Usuario, int(user_id))

    # UPLOAD_FOLDER e MAX_CONTENT_LENGTH já estão em config.py, apenas garanta que o diretório exista
    os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], "documentos"), exist_ok=True)

    db.init_app(app)
    from flask_migrate import Migrate

    Migrate(app, db)

    init_performance_optimizations(app)
    PerformanceMiddleware(app)

    app.register_blueprint(admin_bp)
    app.register_blueprint(pessoa_bp)
    app.register_blueprint(fazenda_bp)
    app.register_blueprint(documento_bp)
    app.register_blueprint(endividamento_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(auditoria_bp)
    app.register_blueprint(test_bp)

    @app.route("/")
    def index():
        return redirect(url_for("admin.index"))

    @app.errorhandler(413)
    def request_entity_too_large(error):
        app.logger.warning(
            f"Tentativa de upload de arquivo muito grande: {request.url}"
        )
        flash(
            f'O arquivo é muito grande. O tamanho máximo permitido é {app.config["MAX_CONTENT_LENGTH"] / (1024 * 1024)}MB.',
            "danger",
        )
        return redirect(request.url)

    @app.errorhandler(400)
    def bad_request(error):
        app.logger.warning(f"Bad request: {error}")
        if "file type not allowed" in str(error).lower():
            flash(
                f'Tipo de arquivo não permitido. Tipos permitidos: {", ".join(["pdf", "png", "jpg", "jpeg", "gif", "doc", "docx", "xls", "xlsx"])}',
                "danger",
            )
        else:
            flash("Requisição inválida. Verifique os dados informados.", "danger")
        return redirect(request.url)

    @app.errorhandler(404)
    def page_not_found(error):
        app.logger.info(f"Página não encontrada: {request.url}")
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        app.logger.error(f"Erro interno do servidor: {error}")
        db.session.rollback()
        return render_template("errors/500.html"), 500

    @app.errorhandler(SQLAlchemyError)
    def handle_db_error(error):
        app.logger.error(f"Erro de banco de dados: {error}")
        db.session.rollback()
        if isinstance(error, IntegrityError):
            flash(
                "Erro de integridade no banco de dados. Verifique se há dados duplicados ou restrições violadas.",
                "danger",
            )
        elif isinstance(error, OperationalError):
            flash(
                "Erro de conexão com o banco de dados. Verifique se o banco está disponível.",
                "danger",
            )
        else:
            flash(
                "Ocorreu um erro no banco de dados. Por favor, tente novamente.",
                "danger",
            )
        return redirect(url_for("admin.index"))

    @app.route("/health")
    def health_check():
        try:
            db.session.execute(text("SELECT 1"))
            
            # Verificar também o Celery/Redis
            celery_status = "disconnected"
            redis_status = "disconnected"
            
            try:
                # Testar conexão com Redis
                import redis
                r = redis.from_url(app.config.get('REDIS_URL', 'redis://localhost:6379/0'))
                r.ping()
                redis_status = "connected"
                
                # Testar Celery
                from celery import current_app as current_celery_app
                i = current_celery_app.control.inspect()
                stats = i.stats()
                if stats:
                    celery_status = "connected"
            except Exception as e:
                app.logger.warning(f"Celery/Redis check failed: {e}")
            
            return jsonify({
                "status": "ok", 
                "database": "connected",
                "redis": redis_status,
                "celery": celery_status,
                "timezone": os.environ.get("TZ", "UTC"),
                "timestamp": datetime.datetime.now().isoformat()
            }), 200
        except Exception as e:
            app.logger.error(f"Erro no health check: {e}")
            return (
                jsonify(
                    {"status": "error", "database": "disconnected", "error": str(e)}
                ),
                500,
            )

    # ========== ROTAS DE TESTE DO CELERY ==========
    @app.route("/test-celery")
    def test_celery():
        """Rota para testar se o Celery está funcionando"""
        try:
            # Usar a tarefa de teste do tasks.py
            from src.utils.tasks import test_celery as celery_test_task
            result = celery_test_task.delay()
            return jsonify({
                "status": "ok",
                "task_id": result.id,
                "message": "Tarefa de teste enviada para processamento"
            })
        except Exception as e:
            app.logger.error(f"Erro ao testar Celery: {e}")
            return jsonify({
                "status": "error",
                "error": str(e)
            }), 500
    
    @app.route("/force-check-notifications")
    def force_check_notifications():
        """Força verificação manual de notificações (útil para debug)"""
        try:
            # Buscar a tarefa registrada no celery
            task = celery.tasks.get('tasks.processar_todas_notificacoes')
            if task:
                result = task.delay()
                return jsonify({
                    "status": "ok",
                    "task_id": result.id,
                    "message": "Verificação de notificações iniciada"
                })
            else:
                # Fallback: executar sincronamente
                from src.utils.notificacao_endividamento_service import NotificacaoEndividamentoService
                from src.utils.notificacao_documentos_service import NotificacaoDocumentoService
                
                service_end = NotificacaoEndividamentoService()
                service_doc = NotificacaoDocumentoService()
                
                count_end = service_end.verificar_e_enviar_notificacoes()
                count_doc = service_doc.verificar_e_enviar_notificacoes()
                
                return jsonify({
                    "status": "ok",
                    "message": "Verificação executada sincronamente",
                    "endividamentos": count_end,
                    "documentos": count_doc,
                    "total": count_end + count_doc
                })
                
        except Exception as e:
            app.logger.error(f"Erro ao forçar verificação: {e}", exc_info=True)
            return jsonify({
                "status": "error",
                "error": str(e)
            }), 500

    @app.route("/celery-status")
    def celery_status():
        """Verifica o status detalhado do Celery"""
        try:
            from celery import current_app as current_celery_app
            i = current_celery_app.control.inspect()
            
            # Obter informações
            stats = i.stats()
            registered = i.registered()
            active = i.active()
            scheduled = i.scheduled()
            
            return jsonify({
                "status": "ok",
                "workers": list(stats.keys()) if stats else [],
                "registered_tasks": registered,
                "active_tasks": active,
                "scheduled_tasks": scheduled,
                "broker_url": app.config.get('CELERY_BROKER_URL', 'not configured')
            })
        except Exception as e:
            return jsonify({
                "status": "error",
                "error": str(e),
                "broker_url": app.config.get('CELERY_BROKER_URL', 'not configured')
            }), 500

    # Rota temporária para testar o template de notificação por e-mail
    @app.route("/testar-email-notificacao")
    def testar_email_notificacao():
        class DummyDoc:
            nome = "Licença Ambiental"
            tipo = type("Tipo", (), {"value": "Certidão"})
            data_emissao = datetime.datetime(2024, 1, 1)
            data_vencimento = datetime.datetime(2024, 12, 31)
            tipo_entidade = type("TipoEntidade", (), {"value": "Fazenda/Área"})
            nome_entidade = "Fazenda Santa Luzia"

        doc = DummyDoc()
        dias_restantes = 5
        from src.utils.email_service import formatar_email_notificacao

        assunto, corpo_html = formatar_email_notificacao(
            doc,
            dias_restantes,
            responsavel="Fulano",
            link_documento="https://meusistema.com/doc/123",
        )
        return corpo_html

    return app

# Criar instância da aplicação
app = create_app()

# Tornar o celery acessível globalmente
if celery is None and app:
    celery = make_celery(app)
    criar_tarefas_notificacao(celery)

if __name__ == "__main__":
    print("Inicialização do Sistema de Gestão de Fazendas")
    port = int(os.environ.get("PORT", 5000))
    app.run(
        debug=os.environ.get("FLASK_DEBUG", "true").lower() in ["true", "on", "1"],
        host="0.0.0.0",
        port=port,
    )