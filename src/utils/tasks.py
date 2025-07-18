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


@celery.task(
    name='tasks.test_celery',
    time_limit=30  # 30 segundos timeout máximo
)
def test_celery() -> Dict[str, Any]:
    """
    Tarefa de teste para verificar funcionamento do Celery
    
    Returns:
        Dicionário com informações de status e ambiente
    """
    try:
        import platform
        import sys
        
        memory_info = {}
        try:
            import psutil
            process = psutil.Process(os.getpid())
            memory_info = {
                "memory_used_mb": process.memory_info().rss / (1024 * 1024),
                "cpu_percent": process.cpu_percent(interval=0.1)
            }
        except ImportError:
            # psutil não está instalado
            pass
        
        return {
            "status": "ok",
            "message": "Celery está funcionando!",
            "timestamp": datetime.now().isoformat(),
            "timezone": os.environ.get('TZ', 'UTC'),
            "system_info": {
                "python_version": sys.version,
                "platform": platform.platform(),
                "hostname": platform.node()
            },
            "task_info": {
                "task_id": celery.current_task.request.id if celery.current_task else None,
                "worker": celery.current_task.request.hostname if celery.current_task else None
            },
            **memory_info
        }
    except Exception as e:
        logger.error(f"Erro ao executar tarefa de teste: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@celery.task(
    name='tasks.limpar_notificacoes_antigas',
    bind=True,
    soft_time_limit=600,  # 10 minutos timeout suave
    time_limit=900,       # 15 minutos timeout forçado
    rate_limit='2/day'    # Máximo 2 execuções por dia
)
def limpar_notificacoes_antigas(self, dias: int = 90) -> Dict[str, Any]:
    """
    Limpa notificações antigas do sistema
    
    Args:
        dias: Idade em dias para considerar uma notificação como antiga
        
    Returns:
        Dicionário com resultados da limpeza
    """
    try:
        from flask import current_app
        from src.models.db import db
        from src.models.notificacao_endividamento import NotificacaoEndividamento, HistoricoNotificacao
        
        start_time = time.time()
        data_limite = datetime.now() - timedelta(days=dias)
        stats = {"notificacoes": 0, "historico": 0}
        
        with current_app.app_context():
            # 1. Limpar notificações antigas enviadas
            try:
                antigas = NotificacaoEndividamento.query.filter(
                    NotificacaoEndividamento.enviado == True,
                    NotificacaoEndividamento.data_envio < data_limite,
                    NotificacaoEndividamento.tipo_notificacao != 'config'  # Manter configurações
                ).all()
                
                for notif in antigas:
                    db.session.delete(notif)
                
                stats["notificacoes"] = len(antigas)
                db.session.commit()
            except Exception as e:
                logger.error(f"Erro ao limpar notificações: {str(e)}")
                db.session.rollback()
            
            # 2. Limpar histórico de notificações antigas
            try:
                historicos = HistoricoNotificacao.query.filter(
                    HistoricoNotificacao.data_envio < data_limite
                ).all()
                
                for hist in historicos:
                    db.session.delete(hist)
                
                stats["historico"] = len(historicos)
                db.session.commit()
            except Exception as e:
                logger.error(f"Erro ao limpar histórico de notificações: {str(e)}")
                db.session.rollback()
        
        total_removido = stats["notificacoes"] + stats["historico"]
        duration = time.time() - start_time
        
        logger.info(
            f"Limpeza concluída em {duration:.2f}s: "
            f"{total_removido} registros removidos "
            f"({stats['notificacoes']} notificações, {stats['historico']} histórico)"
        )
        
        return {
            "status": "success",
            "removidos": {
                "notificacoes": stats["notificacoes"],
                "historico": stats["historico"],
                "total": total_removido
            },
            "dias_limite": dias,
            "data_limite": data_limite.isoformat(),
            "duracao_segundos": duration,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro ao limpar notificações antigas: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@celery.task(
    name='tasks.enviar_relatorio_diario',
    bind=True,
    soft_time_limit=120
)
def enviar_relatorio_diario(self, destinatarios: List[str]) -> Dict[str, Any]:
    """
    Gera e envia um relatório diário por email
    
    Args:
        destinatarios: Lista de emails para receber o relatório
        
    Returns:
        Dicionário com resultado do envio
    """
    try:
        from flask import current_app
        from src.models.documento import Documento
        from src.models.endividamento import Endividamento
        from src.utils.email_service import email_service
        
        start_time = time.time()
        hoje = datetime.now().date()
        
        with current_app.app_context():
            # Buscar documentos vencendo hoje
            documentos_hoje = Documento.query.filter(
                Documento.data_vencimento == hoje
            ).all()
            
            # Buscar documentos vencendo nos próximos 7 dias
            documentos_7dias = Documento.query.filter(
                Documento.data_vencimento > hoje,
                Documento.data_vencimento <= hoje + timedelta(days=7)
            ).all()
            
            # Buscar endividamentos vencendo hoje
            endividamentos_hoje = Endividamento.query.filter(
                Endividamento.data_vencimento_final == hoje
            ).all()
            
            # Buscar endividamentos vencendo nos próximos 7 dias
            endividamentos_7dias = Endividamento.query.filter(
                Endividamento.data_vencimento_final > hoje,
                Endividamento.data_vencimento_final <= hoje + timedelta(days=7)
            ).all()
            
            # Construir relatório HTML
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #f8f9fa; padding: 15px; text-align: center; }}
                    h2 {{ color: #0056b3; }}
                    table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    .alert {{ color: #721c24; background-color: #f8d7da; padding: 10px; border-radius: 4px; }}
                    .warning {{ color: #856404; background-color: #fff3cd; padding: 10px; border-radius: 4px; }}
                    .footer {{ font-size: 12px; color: #6c757d; text-align: center; margin-top: 30px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Relatório Diário - Sistema de Gestão Agrícola</h1>
                        <p>Data: {hoje.strftime('%d/%m/%Y')}</p>
                    </div>
                    
                    <h2>Resumo</h2>
                    <p>Este relatório apresenta os vencimentos do dia e da próxima semana.</p>
                    
                    <div class="alert">
                        <strong>Vencendo Hoje:</strong> {len(documentos_hoje)} documento(s) e {len(endividamentos_hoje)} endividamento(s)
                    </div>
                    
                    <div class="warning">
                        <strong>Vencendo nos próximos 7 dias:</strong> {len(documentos_7dias)} documento(s) e {len(endividamentos_7dias)} endividamento(s)
                    </div>
                    
                    <h2>Documentos Vencendo Hoje</h2>
                    <table>
                        <tr>
                            <th>Nome</th>
                            <th>Tipo</th>
                            <th>Data Vencimento</th>
                        </tr>
                        {"".join(f"<tr><td>{doc.nome}</td><td>{doc.tipo.value if hasattr(doc.tipo, 'value') else doc.tipo}</td><td>{doc.data_vencimento.strftime('%d/%m/%Y')}</td></tr>" for doc in documentos_hoje) if documentos_hoje else "<tr><td colspan='3'>Nenhum documento vencendo hoje</td></tr>"}
                    </table>
                    
                    <h2>Endividamentos Vencendo Hoje</h2>
                    <table>
                        <tr>
                            <th>Banco</th>
                            <th>Proposta</th>
                            <th>Valor</th>
                            <th>Data Vencimento</th>
                        </tr>
                        {"".join(f"<tr><td>{e.banco}</td><td>{e.numero_proposta}</td><td>R$ {e.valor_operacao:,.2f}</td><td>{e.data_vencimento_final.strftime('%d/%m/%Y')}</td></tr>" for e in endividamentos_hoje) if endividamentos_hoje else "<tr><td colspan='4'>Nenhum endividamento vencendo hoje</td></tr>"}
                    </table>
                    
                    <h2>Próximos Vencimentos (7 dias)</h2>
                    <p><strong>Documentos:</strong> {len(documentos_7dias)}</p>
                    <p><strong>Endividamentos:</strong> {len(endividamentos_7dias)}</p>
                    
                    <div class="footer">
                        <p>Este é um email automático do Sistema de Gestão Agrícola.</p>
                        <p>© {hoje.year} - Não responda a esta mensagem.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Enviar email
            assunto = f"Relatório Diário - Vencimentos - {hoje.strftime('%d/%m/%Y')}"
            success = email_service.send_email(
                destinatarios=destinatarios,
                assunto=assunto,
                corpo=html_body,
                html=True
            )
            
            duration = time.time() - start_time
            
            if success:
                logger.info(
                    f"Relatório diário enviado com sucesso para {len(destinatarios)} "
                    f"destinatário(s) em {duration:.2f}s"
                )
            else:
                logger.error(f"Falha ao enviar relatório diário")
                
            return {
                "status": "success" if success else "error",
                "enviado": success,
                "destinatarios": len(destinatarios),
                "itens": {
                    "documentos_hoje": len(documentos_hoje),
                    "documentos_7dias": len(documentos_7dias),
                    "endividamentos_hoje": len(endividamentos_hoje),
                    "endividamentos_7dias": len(endividamentos_7dias)
                },
                "timestamp": datetime.now().isoformat(),
                "duracao_segundos": duration
            }
            
    except Exception as e:
        logger.error(f"Erro ao enviar relatório diário: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# Função auxiliar para importação no main.py
def make_celery(app):
    """
    Compatibilidade com o código existente.
    Retorna a instância do Celery já configurada.
    
    Args:
        app: Aplicação Flask
        
    Returns:
        Instância Celery configurada
    """
    from src.celery_config import celery
    
    # Atualizar contexto se necessário
    class ContextTask(celery.Task):
        abstract = True
        
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    celery.conf.update(app.config)
    
    logger.info("Celery configurado com contexto Flask")
    
    return celery