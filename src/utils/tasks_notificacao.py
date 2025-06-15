# Tarefas agendadas para notificações
from src.utils.notificacao_endividamento_service import NotificacaoEndividamentoService
import logging

logger = logging.getLogger(__name__)

def processar_notificacoes_endividamento():
    """Tarefa agendada para processar notificações de endividamento"""
    try:
        service = NotificacaoEndividamentoService()
        notificacoes_enviadas = service.verificar_e_enviar_notificacoes()
        
        logger.info(f"Processamento de notificações concluído. {notificacoes_enviadas} notificações enviadas.")
        return notificacoes_enviadas
        
    except Exception as e:
        logger.error(f"Erro ao processar notificações agendadas: {str(e)}")
        return 0

