# /src/utils/tasks_notificacao.py

# Tarefas agendadas para notificações
import logging

from src.utils.notificacao_documentos_service import NotificacaoDocumentoService
from src.utils.notificacao_endividamento_service import NotificacaoEndividamentoService

logger = logging.getLogger(__name__)


def processar_notificacoes_endividamento():
    """Tarefa agendada para processar notificações de endividamento"""
    try:
        service = NotificacaoEndividamentoService()
        notificacoes_enviadas = service.verificar_e_enviar_notificacoes()

        logger.info(
            f"Processamento de notificações de endividamento concluído. {notificacoes_enviadas} notificações enviadas."
        )
        return notificacoes_enviadas

    except Exception as e:
        logger.error(
            f"Erro ao processar notificações agendadas de endividamento: {str(e)}"
        )
        return 0


def processar_notificacoes_documentos():
    """Tarefa agendada para processar notificações de documentos"""
    try:
        service = NotificacaoDocumentoService()
        notificacoes_enviadas = service.verificar_e_enviar_notificacoes()

        logger.info(
            f"Processamento de notificações de documentos concluído. {notificacoes_enviadas} notificações enviadas."
        )
        return notificacoes_enviadas

    except Exception as e:
        logger.error(
            f"Erro ao processar notificações agendadas de documentos: {str(e)}"
        )
        return 0
