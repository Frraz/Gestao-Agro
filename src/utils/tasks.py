# Configuração para tarefas em segundo plano com Celery
from celery import Celery
import os

def make_celery(app):
    """Cria instância do Celery configurada com Flask"""
    celery = Celery(
        app.import_name,
        backend=app.config.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
        broker=app.config.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    )
    
    celery.conf.update(app.config)
    
    class ContextTask(celery.Task):
        """Tarefa que executa dentro do contexto da aplicação Flask"""
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    return celery

# Tarefas assíncronas
def send_notification_email(email, subject, body):
    """Envia e-mail de notificação em segundo plano"""
    from flask_mail import Mail, Message
    from flask import current_app
    
    mail = Mail(current_app)
    msg = Message(
        subject=subject,
        recipients=[email],
        body=body,
        sender=current_app.config['MAIL_DEFAULT_SENDER']
    )
    
    try:
        mail.send(msg)
        current_app.logger.info(f'E-mail enviado para {email}: {subject}')
        return True
    except Exception as e:
        current_app.logger.error(f'Erro ao enviar e-mail para {email}: {e}')
        return False

def process_document_upload(document_id, file_path):
    """Processa upload de documento em segundo plano"""
    from flask import current_app
    
    try:
        # Aqui você pode adicionar processamento adicional
        # como extração de texto, validação de conteúdo, etc.
        current_app.logger.info(f'Processando documento {document_id}: {file_path}')
        
        # Exemplo: validar se o arquivo existe
        if not os.path.exists(file_path):
            raise FileNotFoundError(f'Arquivo não encontrado: {file_path}')
        
        # Exemplo: verificar tamanho do arquivo
        file_size = os.path.getsize(file_path)
        if file_size > 50 * 1024 * 1024:  # 50MB
            raise ValueError('Arquivo muito grande')
        
        current_app.logger.info(f'Documento {document_id} processado com sucesso')
        return True
        
    except Exception as e:
        current_app.logger.error(f'Erro ao processar documento {document_id}: {e}')
        return False

