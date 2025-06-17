# /src/main.py

import os
import sys
import logging
import datetime
from logging.handlers import RotatingFileHandler

# Ajuste o sys.path ANTES dos imports locais do projeto:
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from werkzeug.utils import secure_filename

from src.models.db import db
from src.routes.admin import admin_bp
from src.routes.pessoa import pessoa_bp
from src.routes.fazenda import fazenda_bp
from src.routes.documento import documento_bp
from src.routes.endividamento import endividamento_bp
from src.routes.auth import auth_bp
from src.routes.auditoria import auditoria_bp
from src.utils.performance import init_performance_optimizations, PerformanceMiddleware
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from sqlalchemy import text
from flask_login import LoginManager
from src.utils.filters import register_filters
from src.routes.test import test_bp
from dotenv import load_dotenv
load_dotenv()

def configure_logging(app):
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/sistema_fazendas.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Inicialização do Sistema de Gestão de Fazendas')
    return app

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_app(test_config=None):
    app = Flask(__name__)

    register_filters(app)

    print("MAIL_USERNAME:", os.environ.get('MAIL_USERNAME'))
    print("MAIL_DEFAULT_SENDER:", os.environ.get('MAIL_DEFAULT_SENDER'))
    
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    from src.models.usuario import Usuario
    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))

    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or os.urandom(24)
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

    # Configuração do banco de dados
    if test_config is None:
        db_url = os.environ.get('DATABASE_URL')
        if db_url:
            if db_url.startswith("mysql://"):
                db_url = db_url.replace("mysql://", "mysql+pymysql://", 1)
            app.config['SQLALCHEMY_DATABASE_URI'] = db_url
        elif os.environ.get('DB_TYPE') == 'mysql':
            app.config['SQLALCHEMY_DATABASE_URI'] = (
                f"mysql+pymysql://{os.getenv('DB_USERNAME', 'root')}:"
                f"{os.getenv('DB_PASSWORD', 'password')}@"
                f"{os.getenv('DB_HOST', 'localhost')}:"
                f"{os.getenv('DB_PORT', '3306')}/"
                f"{os.getenv('DB_NAME', 'gestao_fazendas')}"
            )
        else:
            app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.dirname(os.path.dirname(__file__)), 'gestao_fazendas.db')
    else:
        app.config.update(test_config)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@gestaofazendas.com.br')
    app.config['REDIS_URL'] = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

    configure_logging(app)

    db.init_app(app)
    from flask_migrate import Migrate
    Migrate(app, db)

    init_performance_optimizations(app)
    PerformanceMiddleware(app)

    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'documentos'), exist_ok=True)

    app.register_blueprint(admin_bp)
    app.register_blueprint(pessoa_bp)
    app.register_blueprint(fazenda_bp)
    app.register_blueprint(documento_bp)
    app.register_blueprint(endividamento_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(auditoria_bp)
    app.register_blueprint(test_bp)

    @app.route('/')
    def index():
        return redirect(url_for('admin.index'))

    @app.errorhandler(413)
    def request_entity_too_large(error):
        app.logger.warning(f'Tentativa de upload de arquivo muito grande: {request.url}')
        flash(f'O arquivo é muito grande. O tamanho máximo permitido é {app.config["MAX_CONTENT_LENGTH"] / (1024 * 1024)}MB.', 'danger')
        return redirect(request.url)

    @app.errorhandler(400)
    def bad_request(error):
        app.logger.warning(f'Bad request: {error}')
        if 'file type not allowed' in str(error).lower():
            flash(f'Tipo de arquivo não permitido. Tipos permitidos: {", ".join(["pdf", "png", "jpg", "jpeg", "gif", "doc", "docx", "xls", "xlsx"])}', 'danger')
        else:
            flash('Requisição inválida. Verifique os dados informados.', 'danger')
        return redirect(request.url)

    @app.errorhandler(404)
    def page_not_found(error):
        app.logger.info(f'Página não encontrada: {request.url}')
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        app.logger.error(f'Erro interno do servidor: {error}')
        db.session.rollback()
        return render_template('errors/500.html'), 500

    @app.errorhandler(SQLAlchemyError)
    def handle_db_error(error):
        app.logger.error(f'Erro de banco de dados: {error}')
        db.session.rollback()
        if isinstance(error, IntegrityError):
            flash('Erro de integridade no banco de dados. Verifique se há dados duplicados ou restrições violadas.', 'danger')
        elif isinstance(error, OperationalError):
            flash('Erro de conexão com o banco de dados. Verifique se o banco está disponível.', 'danger')
        else:
            flash('Ocorreu um erro no banco de dados. Por favor, tente novamente.', 'danger')
        return redirect(url_for('admin.index'))

    with app.app_context():
        try:
            db.create_all()
            app.logger.info('Banco de dados inicializado com sucesso')
        except SQLAlchemyError as e:
            app.logger.error(f'Erro ao inicializar banco de dados: {e}')
            print(f"ERRO: Não foi possível conectar ao banco de dados: {e}")

    @app.route('/health')
    def health_check():
        try:
            db.session.execute(text('SELECT 1'))
            return jsonify({'status': 'ok', 'database': 'connected'}), 200
        except Exception as e:
            app.logger.error(f'Erro no health check: {e}')
            return jsonify({'status': 'error', 'database': 'disconnected', 'error': str(e)}), 500

    # Rota temporária para testar o template de notificação por e-mail
    @app.route('/testar-email-notificacao')
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
        assunto, corpo_html = formatar_email_notificacao(doc, dias_restantes, responsavel="Fulano", link_documento="https://meusistema.com/doc/123")
        return corpo_html

    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    app.run(
        debug=os.environ.get('FLASK_DEBUG', 'true').lower() in ['true', 'on', '1'],
        host='0.0.0.0',
        port=port
    )