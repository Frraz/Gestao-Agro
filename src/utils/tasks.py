# /src/utils/tasks.py

# Configuração para tarefas em segundo plano com Celery
import os
from datetime import timedelta
from celery import Celery, Task
from celery.schedules import crontab

def make_celery(app):
    """Cria instância do Celery configurada com Flask"""
    celery = Celery(
        app.import_name,
        backend=app.config.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
        broker=app.config.get("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    )

    # Configurações do Celery (usando nomes NOVOS)
    celery.conf.update(
        # Configurações básicas
        result_backend=app.config.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
        broker_url=app.config.get("CELERY_BROKER_URL", "redis://localhost:6379/0"),
        
        # Serialização
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        
        # Timezone
        timezone='America/Sao_Paulo',
        enable_utc=True,
        
        # Resultado
        result_expires=3600,
        
        # Beat Schedule
        beat_schedule={
            # Verifica notificações a cada 5 minutos
            'verificar-notificacoes-pendentes': {
                'task': 'tasks.processar_todas_notificacoes',
                'schedule': timedelta(minutes=5),
            },
            # Verificação diária às 8h da manhã
            'verificacao-diaria-notificacoes': {
                'task': 'tasks.processar_todas_notificacoes',
                'schedule': crontab(hour=8, minute=0),
            },
        }
    )

    class ContextTask(celery.Task):
        """Tarefa que executa dentro do contexto da aplicação Flask"""
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    
    # Registrar tarefas após criar o celery
    register_tasks(celery)
    
    return celery


def register_tasks(celery):
    """Registra todas as tarefas no Celery"""
    
    @celery.task(name='src.utils.tasks.verificar_e_enviar_notificacoes')
    def verificar_e_enviar_notificacoes():
        """Verifica e envia todas as notificações pendentes"""
        from flask import current_app
        from src.utils.tasks_notificacao import (
            verificar_notificacoes_endividamento,
            verificar_notificacoes_documentos
        )
        
        try:
            current_app.logger.info("Iniciando verificação de notificações...")
            
            endividamentos_notificados = verificar_notificacoes_endividamento()
            current_app.logger.info(f"Notificações de endividamento processadas: {endividamentos_notificados}")
            
            documentos_notificados = verificar_notificacoes_documentos()
            current_app.logger.info(f"Notificações de documentos processadas: {documentos_notificados}")
            
            return {
                'endividamentos': endividamentos_notificados,
                'documentos': documentos_notificados,
                'total': endividamentos_notificados + documentos_notificados
            }
            
        except Exception as e:
            current_app.logger.error(f"Erro ao verificar notificações: {str(e)}")
            raise

    @celery.task(name='src.utils.tasks.send_notification_email')
    def send_notification_email(email, subject, body):
        """Envia e-mail de notificação em segundo plano"""
        from flask import current_app
        from flask_mail import Mail, Message

        mail = Mail(current_app)
        msg = Message(
            subject=subject,
            recipients=[email],
            body=body,
            sender=current_app.config["MAIL_DEFAULT_SENDER"],
        )

        try:
            mail.send(msg)
            current_app.logger.info(f"E-mail enviado para {email}: {subject}")
            return True
        except Exception as e:
            current_app.logger.error(f"Erro ao enviar e-mail para {email}: {e}")
            return False

    @celery.task(name='src.utils.tasks.process_document_upload')
    def process_document_upload(document_id, file_path):
        """Processa upload de documento em segundo plano"""
        from flask import current_app

        try:
            current_app.logger.info(f"Processando documento {document_id}: {file_path}")

            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

            file_size = os.path.getsize(file_path)
            if file_size > 50 * 1024 * 1024:  # 50MB
                raise ValueError("Arquivo muito grande")

            current_app.logger.info(f"Documento {document_id} processado com sucesso")
            return True

        except Exception as e:
            current_app.logger.error(f"Erro ao processar documento {document_id}: {e}")
            return False

    @celery.task(name='src.utils.tasks.test_celery')
    def test_celery():
        """Tarefa de teste para verificar funcionamento do Celery"""
        from datetime import datetime
        return f"Celery está funcionando! Timestamp: {datetime.now()}"