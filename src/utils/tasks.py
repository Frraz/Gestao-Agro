# /src/utils/tasks.py
"""
Tarefas Celery complementares ao sistema de notificações
Usa a configuração centralizada de celery_config.py
"""
import os
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Union, List

from src.celery_config import celery

logger = logging.getLogger(__name__)


@celery.task(
    name='tasks.send_notification_email',
    bind=True,
    max_retries=3,
    soft_time_limit=30,  # 30 segundos timeout suave
    time_limit=60        # 60 segundos timeout forçado
)
def send_notification_email(
    self, 
    email: Union[str, List[str]], 
    subject: str, 
    body: str, 
    html_body: Optional[str] = None
) -> bool:
    """
    Envia e-mail de notificação em segundo plano
    
    Args:
        email: Email ou lista de emails dos destinatários
        subject: Assunto do email
        body: Corpo do email em texto simples
        html_body: Corpo do email em HTML (opcional)
        
    Returns:
        Boolean indicando sucesso ou falha
    """
    try:
        from flask import current_app
        from src.utils.email_service import email_service
        
        start_time = time.time()
        destinatarios = [email] if isinstance(email, str) else email
        
        # Usar o serviço de email existente
        success = email_service.send_email(
            destinatarios=destinatarios,
            assunto=subject,
            corpo=html_body if html_body else body,
            html=bool(html_body)
        )
        
        duration = time.time() - start_time
        
        if success:
            logger.info(
                f"E-mail enviado para {len(destinatarios)} destinatário(s): "
                f"'{subject}' ({duration:.2f}s)"
            )
        else:
            logger.error(f"Falha ao enviar e-mail para {email}: '{subject}'")
            
            # Tenta novamente (retry) após um tempo
            if self.request.retries < self.max_retries:
                raise self.retry(
                    exc=Exception("Falha ao enviar email"), 
                    countdown=60 * (2 ** self.request.retries)
                )
            
        return success
        
    except Exception as e:
        logger.error(f"Erro ao enviar e-mail para {email}: {str(e)}", exc_info=True)
        
        # Tenta novamente (retry) se não for o último retry
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
            
        return False


@celery.task(
    name='tasks.process_document_upload',
    bind=True,
    max_retries=2,
    soft_time_limit=300,  # 5 minutos timeout suave
    time_limit=600        # 10 minutos timeout forçado
)
def process_document_upload(
    self, 
    document_id: int, 
    file_path: str, 
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Processa upload de documento em segundo plano
    
    Args:
        document_id: ID do documento no banco de dados
        file_path: Caminho para o arquivo no sistema
        metadata: Metadados adicionais sobre o arquivo (opcional)
    
    Returns:
        Dicionário com resultado do processamento
    """
    try:
        from flask import current_app
        from src.models.db import db
        from src.models.documento import Documento
        
        start_time = time.time()
        logger.info(f"Processando documento {document_id}: {file_path}")
        
        # Verificar se o arquivo existe
        if not os.path.exists(file_path):
            error_msg = f"Arquivo não encontrado: {file_path}"
            logger.error(error_msg)
            
            # Atualizar o status do documento no banco de dados
            try:
                with current_app.app_context():
                    documento = Documento.query.get(document_id)
                    if documento:
                        documento.status_processamento = "erro"
                        documento.erro_processamento = error_msg
                        db.session.commit()
            except Exception as db_error:
                logger.error(f"Erro ao atualizar status do documento: {db_error}")
                
            return {
                "success": False,
                "error": error_msg,
                "document_id": document_id
            }
        
        # Verificar tamanho do arquivo
        file_size = os.path.getsize(file_path)
        if file_size > 50 * 1024 * 1024:  # 50MB
            error_msg = f"Arquivo muito grande: {file_size / (1024 * 1024):.2f} MB"
            logger.error(error_msg)
            
            # Atualizar o status do documento no banco de dados
            try:
                with current_app.app_context():
                    documento = Documento.query.get(document_id)
                    if documento:
                        documento.status_processamento = "erro"
                        documento.erro_processamento = error_msg
                        db.session.commit()
            except Exception as db_error:
                logger.error(f"Erro ao atualizar status do documento: {db_error}")
                
            return {
                "success": False,
                "error": error_msg,
                "document_id": document_id,
                "file_size_mb": file_size / (1024 * 1024)
            }
            
        # TODO: Implementar o processamento real do arquivo aqui
        # Exemplos: extração de texto, geração de thumbnail, verificação de vírus, etc.
        
        # Simulação de processamento bem-sucedido
        time.sleep(1)  # Simular algum processamento
        
        # Atualizar o status do documento no banco de dados
        try:
            with current_app.app_context():
                documento = Documento.query.get(document_id)
                if documento:
                    documento.status_processamento = "concluido"
                    documento.data_processamento = datetime.now()
                    if hasattr(documento, 'tamanho_arquivo'):
                        documento.tamanho_arquivo = file_size
                    db.session.commit()
        except Exception as db_error:
            logger.error(f"Erro ao atualizar status do documento: {db_error}")
        
        duration = time.time() - start_time
        logger.info(
            f"Documento {document_id} processado com sucesso em {duration:.2f}s. "
            f"Tamanho: {file_size / 1024:.2f} KB"
        )
        
        return {
            "success": True,
            "document_id": document_id,
            "file_size": file_size,
            "processing_time": duration,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro ao processar documento {document_id}: {str(e)}", exc_info=True)
        
        # Tenta novamente (retry) se não for o último retry
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        
        # Atualizar status para erro no banco de dados
        try:
            from flask import current_app
            from src.models.db import db
            from src.models.documento import Documento
            
            with current_app.app_context():
                documento = Documento.query.get(document_id)
                if documento:
                    documento.status_processamento = "erro"
                    documento.erro_processamento = str(e)
                    db.session.commit()
        except Exception as db_error:
            logger.error(f"Erro ao atualizar status do documento: {db_error}")
        
        return {
            "success": False,
            "error": str(e),
            "document_id": document_id,
            "timestamp": datetime.now().isoformat()
        }


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
