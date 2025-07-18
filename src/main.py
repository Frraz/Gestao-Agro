# /src/main.py

import os
import sys
import datetime
import logging
import time
from typing import Optional

from logging.handlers import RotatingFileHandler

from src.api_docs import init_docs


# Ajuste o sys.path ANTES dos imports locais do projeto:
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Configurar timezone
os.environ["TZ"] = "America/Sao_Paulo"
try:
    time.tzset()  # Só funciona em Unix/Linux (como Railway)
except AttributeError:
    pass  # Ignora em sistemas onde tzset não está disponível

from dotenv import load_dotenv

# Carrega variáveis de ambiente ANTES de outros imports
load_dotenv()

# ========== IMPORTAR CELERY DO ARQUIVO CENTRALIZADO ==========
from src.celery_config import celery, make_celery

# Agora importar o Flask e outros módulos
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from flask_login import LoginManager, login_required, current_user
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
# Importar Flask-WTF para proteção CSRF
from flask_wtf.csrf import CSRFProtect

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
from src.utils.tasks_notificacao import criar_tarefas_notificacao

# Inicializar proteção CSRF
csrf = CSRFProtect()


def configure_logging(app: Flask) -> Flask:
    """Configura o sistema de logging da aplicação"""
    if not os.path.exists("logs"):
        os.makedirs("logs")
    
    # Handler para arquivo
    file_handler = RotatingFileHandler(
        "logs/sistema_fazendas.log", 
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
        )
    )
    file_handler.setLevel(logging.INFO)
    
    # Handler para erros críticos
    error_file_handler = RotatingFileHandler(
        "logs/errors.log",
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    error_file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s: %(message)s\n"
            "%(pathname)s:%(lineno)d\n"
            "%(exc_info)s\n"
        )
    )
    error_file_handler.setLevel(logging.ERROR)
    
    app.logger.addHandler(file_handler)
    app.logger.addHandler(error_file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info("Inicialização do Sistema de Gestão de Fazendas")
    
    return app


def allowed_file(filename: str) -> bool:
    """Verifica se o arquivo tem extensão permitida"""
    ALLOWED_EXTENSIONS = {
        "pdf", "png", "jpg", "jpeg", "gif",
        "doc", "docx", "xls", "xlsx"
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

    # Garantir que SECRET_KEY está definido (necessário para CSRF e sessões)
    if "SECRET_KEY" not in app.config or not app.config["SECRET_KEY"]:
        app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "chave-secreta-temporaria-nao-usar-em-producao")

    if test_config:
        app.config.update(test_config)

    # Configurar logging ANTES de usar app.logger
    configure_logging(app)

    # Registrar filtros Jinja2
    register_filters(app)

    # ========== ATUALIZAR CELERY COM CONTEXTO DO FLASK ==========
    global celery
    celery = make_celery(app)

    # Registrar tarefas de notificação
    criar_tarefas_notificacao(celery)

    # Log de confirmação
    app.logger.info(f"Celery inicializado com broker: {app.config.get('CELERY_BROKER_URL')}")
    app.logger.info(f"Tarefas registradas: {list(celery_tasks.keys())}")

    # Inicializar proteção CSRF
    csrf.init_app(app)
    
    # Configurar Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Por favor, faça login para acessar esta página."
    login_manager.login_message_category = "info"

    from src.models.usuario import Usuario

    @login_manager.user_loader
    def load_user(user_id: str) -> Optional[Usuario]:
        return db.session.get(Usuario, int(user_id))

    # Criar diretórios necessários
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], "documentos"), exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    # Inicializar extensões
    db.init_app(app)
    
    from flask_migrate import Migrate
    Migrate(app, db)

    # Otimizações de performance
    init_performance_optimizations(app)
    PerformanceMiddleware(app)

    # Registrar blueprints
    app.register_blueprint(admin_bp)
    app.register_blueprint(pessoa_bp)
    app.register_blueprint(fazenda_bp)
    app.register_blueprint(documento_bp)
    app.register_blueprint(endividamento_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(auditoria_bp)
    app.register_blueprint(test_bp)

    # Inicializar documentação da API (apenas uma vez)
    if app.config.get('ENABLE_API_DOCS', True):
        init_docs(app)

    # ========== ROTAS PRINCIPAIS ==========
    
    @app.route("/")
    def index():
        return redirect(url_for("admin.index"))
    
    @app.route("/clear-cache")
    @login_required
    def clear_cache():
        """Limpa o cache Redis (apenas para admins)"""
        if not current_user.is_admin:
            return jsonify({"status": "error", "error": "Acesso negado"}), 403
            
        try:
            from src.utils.cache import cache
            cache.clear()
            app.logger.info(f"Cache limpo por {current_user.nome}")
            return jsonify({
                "status": "ok", 
                "message": "Cache limpo com sucesso",
                "timestamp": datetime.datetime.now().isoformat()
            })
        except Exception as e:
            app.logger.error(f"Erro ao limpar cache: {e}")
            return jsonify({"status": "error", "error": str(e)}), 500

    # ========== ERROR HANDLERS ==========
    
    @app.errorhandler(413)
    def request_entity_too_large(error):
        app.logger.warning(f"Upload muito grande: {request.url}")
        max_size_mb = app.config["MAX_CONTENT_LENGTH"] / (1024 * 1024)
        flash(
            f'O arquivo é muito grande. O tamanho máximo permitido é {max_size_mb:.0f}MB.',
            "danger"
        )
        return redirect(request.referrer or url_for("admin.index"))

    @app.errorhandler(400)
    def bad_request(error):
        app.logger.warning(f"Bad request: {error}")
        if "file type not allowed" in str(error).lower():
            flash(
                'Tipo de arquivo não permitido. Tipos permitidos: PDF, imagens (PNG, JPG, GIF) e documentos Office.',
                "danger"
            )
        else:
            flash("Requisição inválida. Verifique os dados informados.", "danger")
        return redirect(request.referrer or url_for("admin.index"))

    @app.errorhandler(404)
    def page_not_found(error):
        app.logger.info(f"Página não encontrada: {request.url}")
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        app.logger.error(f"Erro interno do servidor: {error}", exc_info=True)
        db.session.rollback()
        return render_template("errors/500.html"), 500

    @app.errorhandler(SQLAlchemyError)
    def handle_db_error(error):
        app.logger.error(f"Erro de banco de dados: {error}", exc_info=True)
        db.session.rollback()
        
        if isinstance(error, IntegrityError):
            flash(
                "Erro de integridade no banco de dados. Verifique se há dados duplicados ou restrições violadas.",
                "danger"
            )
        elif isinstance(error, OperationalError):
            flash(
                "Erro de conexão com o banco de dados. Por favor, tente novamente em alguns instantes.",
                "danger"
            )
        else:
            flash(
                "Ocorreu um erro no banco de dados. Por favor, tente novamente.",
                "danger"
            )
        return redirect(url_for("admin.index"))

    # ========== HEALTH CHECK E MONITORAMENTO ==========
    
    @app.route("/health")
    def health_check():
        """Endpoint de health check para monitoramento"""
        try:
            # Testar banco de dados
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
                "workers": workers
            },
            "version": app.config.get("VERSION", "1.0.0")
        }
        
        return jsonify(response), 200 if all_connected else 503

    @app.route("/test-celery")
    def test_celery_route():
        """Rota para testar se o Celery está funcionando"""
        try:
            # Tentar diferentes tarefas de teste
            test_tasks = ['tasks.test_celery', 'tasks.test_notificacoes']
            
            for task_name in test_tasks:
                task = celery.tasks.get(task_name)
                if task:
                    result = task.delay()
                    return jsonify({
                        "status": "ok",
                        "task_id": result.id,
                        "task_name": task_name,
                        "message": "Tarefa de teste enviada para processamento",
                        "timestamp": datetime.datetime.now().isoformat()
                    })
            
            # Se nenhuma tarefa de teste foi encontrada
            available_tasks = [t for t in celery.tasks.keys() if not t.startswith('celery.')]
            return jsonify({
                "status": "error",
                "error": "Nenhuma tarefa de teste encontrada",
                "available_tasks": available_tasks
            }), 500
            
        except Exception as e:
            app.logger.error(f"Erro ao testar Celery: {e}", exc_info=True)
            return jsonify({
                "status": "error",
                "error": str(e),
                "timestamp": datetime.datetime.now().isoformat()
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
                    "message": "Verificação de notificações iniciada",
                    "timestamp": datetime.datetime.now().isoformat()
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
                    "resultado": resultado,
                    "timestamp": datetime.datetime.now().isoformat()
                })

        except Exception as e:
            app.logger.error(f"Erro ao forçar verificação: {e}", exc_info=True)
            return jsonify({
                "status": "error",
                "error": str(e),
                "timestamp": datetime.datetime.now().isoformat()
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
                "workers": list(stats.keys()),
                "worker_stats": stats,
                "registered_tasks": registered,
                "active_tasks": active,
                "scheduled_tasks": scheduled,
                "reserved_tasks": reserved,
                "local_tasks": local_tasks,
                "beat_schedule": beat_schedule,
                "broker_url": app.config.get('CELERY_BROKER_URL', 'not configured'),
                "timezone": celery.conf.timezone,
                "timestamp": datetime.datetime.now().isoformat()
            })
        except Exception as e:
            app.logger.error(f"Erro ao verificar status do Celery: {e}")
            return jsonify({
                "status": "error",
                "error": str(e),
                "broker_url": app.config.get('CELERY_BROKER_URL', 'not configured'),
                "timestamp": datetime.datetime.now().isoformat()
            }), 500

    @app.route("/notification-dashboard")
    def notification_dashboard():
        """Dashboard de notificações pendentes e próximas"""
        try:
            from src.models.notificacao_endividamento import NotificacaoEndividamento
            from src.models.endividamento import Endividamento
            from sqlalchemy import and_
            
            # Filtrar notificações reais (excluir configurações)
            base_filter = and_(
                NotificacaoEndividamento.tipo_notificacao != 'config',
                NotificacaoEndividamento.ativo == True
            )
            
            # Notificações pendentes (atrasadas)
            pendentes = NotificacaoEndividamento.query.filter(
                base_filter,
                NotificacaoEndividamento.enviado == False,
                NotificacaoEndividamento.data_envio <= datetime.datetime.utcnow()
            ).all()
            
            # Próximas notificações (futuras)
            proximas = NotificacaoEndividamento.query.filter(
                base_filter,
                NotificacaoEndividamento.enviado == False,
                NotificacaoEndividamento.data_envio > datetime.datetime.utcnow()
            ).order_by(NotificacaoEndividamento.data_envio).limit(10).all()
            
            # Estatísticas (excluindo configurações)
            total_notif = NotificacaoEndividamento.query.filter(
                NotificacaoEndividamento.tipo_notificacao != 'config'
            ).count()
            
            enviadas = NotificacaoEndividamento.query.filter(
                NotificacaoEndividamento.tipo_notificacao != 'config',
                NotificacaoEndividamento.enviado == True
            ).count()
            
            ativas = NotificacaoEndividamento.query.filter(
                base_filter,
                NotificacaoEndividamento.enviado == False
            ).count()
            
            # Notificações com falha
            falhas = NotificacaoEndividamento.query.filter(
                base_filter,
                NotificacaoEndividamento.enviado == False,
                NotificacaoEndividamento.tentativas >= 3
            ).count()
            
            return jsonify({
                "status": "ok",
                "stats": {
                    "total": total_notif,
                    "enviadas": enviadas,
                    "ativas": ativas,
                    "pendentes": len(pendentes),
                    "falhas": falhas
                },
                "pendentes": [
                    {
                        "id": n.id,
                        "endividamento": n.endividamento.banco if n.endividamento else "N/A",
                        "tipo": n.tipo_notificacao,
                        "data_envio": n.data_envio.isoformat() if n.data_envio else None,
                        "tentativas": n.tentativas,
                        "atraso_horas": int((datetime.datetime.utcnow() - n.data_envio).total_seconds() / 3600)
                    } for n in pendentes[:5]
                ],
                "proximas": [
                    {
                        "id": n.id,
                        "endividamento": n.endividamento.banco if n.endividamento else "N/A",
                        "tipo": n.tipo_notificacao,
                        "data_envio": n.data_envio.isoformat() if n.data_envio else None,
                        "horas_restantes": int((n.data_envio - datetime.datetime.utcnow()).total_seconds() / 3600)
                    } for n in proximas
                ],
                "timestamp": datetime.datetime.now().isoformat()
            })
        except Exception as e:
            app.logger.error(f"Erro no dashboard de notificações: {e}", exc_info=True)
            return jsonify({
                "status": "error",
                "error": str(e),
                "timestamp": datetime.datetime.now().isoformat()
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
        
        assunto, corpo_html = formatar_email_notificacao(
            doc,
            dias_restantes,
            responsavel="Fulano de Tal",
            link_documento="https://meusistema.com/doc/123",
        )
        
        # Adicionar informações de debug
        debug_html = f"""
        <div style="background: #f0f0f0; padding: 20px; margin-top: 40px;">
            <h3>Informações de Debug</h3>
            <p><strong>Assunto:</strong> {assunto}</p>
            <p><strong>Data/Hora:</strong> {datetime.datetime.now()}</p>
            <p><strong>Timezone:</strong> {os.environ.get('TZ', 'UTC')}</p>
        </div>
        """
        
        return corpo_html + debug_html

    return app


# Criar instância da aplicação
app = create_app()

# Garantir que o celery está disponível globalmente para o worker
if not hasattr(app, 'celery'):
    app.celery = celery

if __name__ == "__main__":
    print("=" * 50)
    print("Sistema de Gestão de Fazendas")
    print("=" * 50)
    print(f"Timezone: {os.environ.get('TZ', 'UTC')}")
    print(f"Redis URL: {os.environ.get('REDIS_URL', 'não configurado')}")
    print(f"Environment: {os.environ.get('FLASK_ENV', 'development')}")
    print(f"Debug Mode: {os.environ.get('FLASK_DEBUG', 'true')}")
    print("=" * 50)
    
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "true").lower() in ["true", "on", "1"]
    
    app.run(
        debug=debug,
        host="0.0.0.0",
        port=port,
    )
