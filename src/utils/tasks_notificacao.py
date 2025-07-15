# /src/utils/tasks_notificacao.py

# /src/utils/tasks_notificacao.py

# Tarefas agendadas para notificações
import logging
from datetime import datetime
from flask import current_app

logger = logging.getLogger(__name__)

# Variável para armazenar as tarefas do Celery
celery_tasks = {}


def criar_tarefas_notificacao(celery):
    """Cria e registra as tarefas de notificação no Celery"""
    
    @celery.task(name='tasks.processar_notificacoes_endividamento', bind=True, max_retries=3)
    def processar_notificacoes_endividamento(self):
        """Tarefa agendada para processar notificações de endividamento"""
        from src.utils.notificacao_endividamento_service import NotificacaoEndividamentoService
        
        try:
            with current_app.app_context():
                logger.info(f"[{self.request.id}] Iniciando processamento de notificações de endividamento - {datetime.now()}")
                
                service = NotificacaoEndividamentoService()
                notificacoes_enviadas = service.verificar_e_enviar_notificacoes()

                logger.info(
                    f"[{self.request.id}] Processamento de notificações de endividamento concluído. "
                    f"{notificacoes_enviadas} notificações enviadas."
                )
                return {
                    'status': 'success',
                    'notificacoes_enviadas': notificacoes_enviadas,
                    'timestamp': datetime.now().isoformat(),
                    'task_id': self.request.id
                }

        except Exception as e:
            logger.error(
                f"[{self.request.id}] Erro ao processar notificações de endividamento: {str(e)}",
                exc_info=True
            )
            # Retry com backoff exponencial
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))

    @celery.task(name='tasks.processar_notificacoes_documentos', bind=True, max_retries=3)
    def processar_notificacoes_documentos(self):
        """Tarefa agendada para processar notificações de documentos"""
        from src.utils.notificacao_documentos_service import NotificacaoDocumentoService
        
        try:
            with current_app.app_context():
                logger.info(f"[{self.request.id}] Iniciando processamento de notificações de documentos - {datetime.now()}")
                
                service = NotificacaoDocumentoService()
                notificacoes_enviadas = service.verificar_e_enviar_notificacoes()

                logger.info(
                    f"[{self.request.id}] Processamento de notificações de documentos concluído. "
                    f"{notificacoes_enviadas} notificações enviadas."
                )
                return {
                    'status': 'success',
                    'notificacoes_enviadas': notificacoes_enviadas,
                    'timestamp': datetime.now().isoformat(),
                    'task_id': self.request.id
                }

        except Exception as e:
            logger.error(
                f"[{self.request.id}] Erro ao processar notificações de documentos: {str(e)}",
                exc_info=True
            )
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))

    @celery.task(name='tasks.processar_todas_notificacoes', bind=True)
    def processar_todas_notificacoes(self):
        """Processa todas as notificações pendentes (endividamentos e documentos)"""
        try:
            with current_app.app_context():
                logger.info(f"[{self.request.id}] === INICIANDO PROCESSAMENTO DE TODAS AS NOTIFICAÇÕES ===")
                
                # Processar notificações de endividamento
                try:
                    resultado_endividamento = processar_notificacoes_endividamento.apply().get()
                except Exception as e:
                    logger.error(f"Erro em notificações de endividamento: {e}")
                    resultado_endividamento = {'notificacoes_enviadas': 0, 'status': 'error', 'error': str(e)}
                
                # Processar notificações de documentos
                try:
                    resultado_documentos = processar_notificacoes_documentos.apply().get()
                except Exception as e:
                    logger.error(f"Erro em notificações de documentos: {e}")
                    resultado_documentos = {'notificacoes_enviadas': 0, 'status': 'error', 'error': str(e)}
                
                total_enviadas = (
                    resultado_endividamento.get('notificacoes_enviadas', 0) +
                    resultado_documentos.get('notificacoes_enviadas', 0)
                )
                
                logger.info(
                    f"[{self.request.id}] === PROCESSAMENTO CONCLUÍDO === "
                    f"Total de notificações enviadas: {total_enviadas}"
                )
                
                return {
                    'status': 'success',
                    'endividamento': resultado_endividamento,
                    'documentos': resultado_documentos,
                    'total_enviadas': total_enviadas,
                    'timestamp': datetime.now().isoformat(),
                    'task_id': self.request.id
                }
                
        except Exception as e:
            logger.error(f"[{self.request.id}] Erro crítico ao processar todas as notificações: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'task_id': self.request.id
            }

    @celery.task(name='tasks.test_notificacoes')
    def test_notificacoes():
        """Testa se o sistema de notificações está acessível"""
        try:
            with current_app.app_context():
                from src.models.notificacao_endividamento import NotificacaoEndividamento
                from src.models.endividamento import Endividamento
                from src.models.documento import Documento
                
                # Conta notificações pendentes de endividamento
                notif_endividamento = NotificacaoEndividamento.query.filter_by(
                    ativo=True
                ).count()
                
                # Conta endividamentos ativos
                endividamentos_ativos = Endividamento.query.filter(
                    Endividamento.data_vencimento_final > datetime.now().date()
                ).count()
                
                # Conta documentos com vencimento
                docs_com_vencimento = Documento.query.filter(
                    Documento.data_vencimento.isnot(None)
                ).count()
                
                return {
                    'status': 'ok',
                    'notificacoes_endividamento_ativas': notif_endividamento,
                    'endividamentos_ativos': endividamentos_ativos,
                    'documentos_com_vencimento': docs_com_vencimento,
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    # Armazenar referências das tarefas
    global celery_tasks
    celery_tasks = {
        'processar_notificacoes_endividamento': processar_notificacoes_endividamento,
        'processar_notificacoes_documentos': processar_notificacoes_documentos,
        'processar_todas_notificacoes': processar_todas_notificacoes,
        'test_notificacoes': test_notificacoes
    }
    
    return celery_tasks


# Funções auxiliares para execução direta (sem Celery)
def processar_notificacoes_endividamento():
    """Executa diretamente o serviço de notificações de endividamento"""
    from src.utils.notificacao_endividamento_service import NotificacaoEndividamentoService
    service = NotificacaoEndividamentoService()
    return service.verificar_e_enviar_notificacoes()

def processar_notificacoes_documentos():
    """Executa diretamente o serviço de notificações de documentos"""
    from src.utils.notificacao_documentos_service import NotificacaoDocumentoService
    service = NotificacaoDocumentoService()
    return service.verificar_e_enviar_notificacoes()