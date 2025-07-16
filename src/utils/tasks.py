# /src/utils/tasks.py

import os
from datetime import timedelta
from celery import Celery
from celery.schedules import crontab

# Para rodar celery puro (sem Flask), pega configs do ambiente
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
TIMEZONE = os.environ.get('TZ', 'America/Sao_Paulo')

celery = Celery(
    "gestao_agro",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
)

celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone=TIMEZONE,
    enable_utc=True,
    result_expires=3600,
    beat_schedule={
        # Executa a cada 5 minutos
        'verificar-notificacoes-pendentes': {
            'task': 'src.utils.tasks.verificar_e_enviar_notificacoes',
            'schedule': timedelta(minutes=5),
        },
        # Executa todo dia às 8h da manhã
        'verificacao-diaria-notificacoes': {
            'task': 'src.utils.tasks.verificar_e_enviar_notificacoes',
            'schedule': crontab(hour=8, minute=0),
        },
    }
)

@celery.task(name='src.utils.tasks.verificar_e_enviar_notificacoes')
def verificar_e_enviar_notificacoes():
    """Verifica e envia todas as notificações pendentes"""
    try:
        # Importações locais para evitar problemas de importação circular
        from src.utils.tasks_notificacao import (
            verificar_notificacoes_endividamento,
            verificar_notificacoes_documentos
        )
        endividamentos_notificados = verificar_notificacoes_endividamento()
        documentos_notificados = verificar_notificacoes_documentos()
        return {
            'endividamentos': endividamentos_notificados,
            'documentos': documentos_notificados,
            'total': endividamentos_notificados + documentos_notificados
        }
    except Exception as e:
        # Não depende do Flask logger, loga direto
        print(f"[Celery] Erro ao verificar notificações: {e}")
        raise

@celery.task(name='src.utils.tasks.send_notification_email')
def send_notification_email(email, subject, body):
    """Envia e-mail de notificação em segundo plano"""
    try:
        # Se rodando em contexto Flask, pode usar current_app, senão, use SMTP direto
        from flask import current_app
        from flask_mail import Mail, Message
        mail = Mail(current_app)
        msg = Message(
            subject=subject,
            recipients=[email],
            body=body,
            sender=current_app.config["MAIL_DEFAULT_SENDER"],
        )
        mail.send(msg)
        current_app.logger.info(f"E-mail enviado para {email}: {subject}")
        return True
    except Exception as e:
        print(f"[Celery] Erro ao enviar e-mail para {email}: {e}")
        return False

@celery.task(name='src.utils.tasks.process_document_upload')
def process_document_upload(document_id, file_path):
    """Processa upload de documento em segundo plano"""
    try:
        print(f"[Celery] Processando documento {document_id}: {file_path}")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
        file_size = os.path.getsize(file_path)
        if file_size > 50 * 1024 * 1024:  # 50MB
            raise ValueError("Arquivo muito grande")
        print(f"[Celery] Documento {document_id} processado com sucesso")
        return True
    except Exception as e:
        print(f"[Celery] Erro ao processar documento {document_id}: {e}")
        return False

@celery.task(name='src.utils.tasks.test_celery')
def test_celery():
    """Tarefa de teste para verificar funcionamento do Celery"""
    from datetime import datetime
    return f"Celery está funcionando! Timestamp: {datetime.now()}"

# Para integração com Flask, use make_celery(app) no seu main.py (não afeta uso standalone do celery)
def make_celery(app):
    """Integra Celery com contexto Flask se necessário."""
    celery.conf.update(
        result_backend=app.config.get("CELERY_RESULT_BACKEND", CELERY_RESULT_BACKEND),
        broker_url=app.config.get("CELERY_BROKER_URL", CELERY_BROKER_URL),
    )
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    celery.Task = ContextTask
    return celery