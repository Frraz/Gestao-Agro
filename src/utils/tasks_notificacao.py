# /src/utils/tasks_notificacao.py

"""
Tarefas agendadas para notificações via Celery
Define jobs para processamento assíncrono de notificações de documentos e endividamentos
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from celery import Task
from flask import current_app
from sqlalchemy import and_

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
                start_time = datetime.now()
                task_id = self.request.id

                logger.info(f"[{task_id}] Iniciando processamento de notificações de endividamento - {start_time}")

                service = NotificacaoEndividamentoService()
                notificacoes_enviadas = service.verificar_e_enviar_notificacoes()

                duration = (datetime.now() - start_time).total_seconds()

                if duration > 60:
                    logger.warning(
                        f"[{task_id}] Processamento de notificações de endividamento demorou {duration:.2f}s"
                    )

                logger.info(
                    f"[{task_id}] Processamento de notificações de endividamento concluído. "
                    f"{notificacoes_enviadas} notificações enviadas em {duration:.2f}s"
                )

                return {
                    'status': 'success',
                    'notificacoes_enviadas': notificacoes_enviadas,
                    'duration_seconds': duration,
                    'timestamp': datetime.now().isoformat(),
                    'task_id': task_id
                }

        except Exception as e:
            logger.error(
                f"[{self.request.id}] Erro ao processar notificações de endividamento: {str(e)}",
                exc_info=True
            )
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

    @celery.task(name='tasks.processar_notificacoes_documentos', bind=True, max_retries=3)
    def processar_notificacoes_documentos(self):
        """Tarefa agendada para processar notificações de documentos"""
        from src.utils.notificacao_documentos_service import NotificacaoDocumentoService

        try:
            with current_app.app_context():
                start_time = datetime.now()
                task_id = self.request.id

                logger.info(f"[{task_id}] Iniciando processamento de notificações de documentos - {start_time}")

                service = NotificacaoDocumentoService()
                notificacoes_enviadas = service.verificar_e_enviar_notificacoes()

                duration = (datetime.now() - start_time).total_seconds()

                if duration > 60:
                    logger.warning(
                        f"[{task_id}] Processamento de notificações de documentos demorou {duration:.2f}s"
                    )

                logger.info(
                    f"[{task_id}] Processamento de notificações de documentos concluído. "
                    f"{notificacoes_enviadas} notificações enviadas em {duration:.2f}s"
                )

                return {
                    'status': 'success',
                    'notificacoes_enviadas': notificacoes_enviadas,
                    'duration_seconds': duration,
                    'timestamp': datetime.now().isoformat(),
                    'task_id': task_id
                }

        except Exception as e:
            logger.error(
                f"[{self.request.id}] Erro ao processar notificações de documentos: {str(e)}",
                exc_info=True
            )
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

    @celery.task(
        name='tasks.processar_todas_notificacoes',
        bind=True,
        soft_time_limit=600,
        time_limit=900
    )
    def processar_todas_notificacoes(self) -> Dict[str, Any]:
        """
        Processa todas as notificações pendentes (endividamentos e documentos)
        """
        try:
            with current_app.app_context():
                start_time = datetime.now()
                task_id = self.request.id

                logger.info(f"[{task_id}] === INICIANDO PROCESSAMENTO DE TODAS AS NOTIFICAÇÕES ===")

                try:
                    resultado_endividamento = processar_notificacoes_endividamento.apply_async().get(timeout=300)
                except Exception as e:
                    logger.error(f"Erro em notificações de endividamento: {e}")
                    resultado_endividamento = {'notificacoes_enviadas': 0, 'status': 'error', 'error': str(e)}

                try:
                    resultado_documentos = processar_notificacoes_documentos.apply_async().get(timeout=300)
                except Exception as e:
                    logger.error(f"Erro em notificações de documentos: {e}")
                    resultado_documentos = {'notificacoes_enviadas': 0, 'status': 'error', 'error': str(e)}

                duration = (datetime.now() - start_time).total_seconds()
                total_enviadas = (
                    resultado_endividamento.get('notificacoes_enviadas', 0) +
                    resultado_documentos.get('notificacoes_enviadas', 0)
                )

                logger.info(
                    f"[{task_id}] === PROCESSAMENTO CONCLUÍDO === "
                    f"Total de notificações enviadas: {total_enviadas} em {duration:.2f}s"
                )

                return {
                    'status': 'success',
                    'endividamento': resultado_endividamento,
                    'documentos': resultado_documentos,
                    'total_enviadas': total_enviadas,
                    'duration_seconds': duration,
                    'timestamp': datetime.now().isoformat(),
                    'task_id': task_id
                }

        except Exception as e:
            logger.error(
                f"[{self.request.id}] Erro crítico ao processar todas as notificações: {str(e)}",
                exc_info=True
            )
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'task_id': self.request.id
            }

    @celery.task(
        name='tasks.test_notificacoes',
        time_limit=30
    )
    def test_notificacoes() -> Dict[str, Any]:
        """
        Testa se o sistema de notificações está acessível
        """
        try:
            with current_app.app_context():
                from src.models.notificacao_endividamento import NotificacaoEndividamento
                from src.models.endividamento import Endividamento
                from src.models.documento import Documento

                notif_endividamento_pendentes = NotificacaoEndividamento.query.filter_by(
                    ativo=True
                ).count()
                endividamentos_ativos = Endividamento.query.filter(
                    Endividamento.data_vencimento_final > datetime.now().date()
                ).count()
                docs_vencimento_proximo = Documento.query.filter(
                    Documento.data_vencimento.isnot(None)
                ).count()
                docs_vencidos = Documento.query.filter(
                    Documento.data_vencimento < datetime.now().date()
                ).count()
                query_time = 0.0  # Aqui você pode calcular o tempo das queries se desejar

                def obter_status_banco_dados():
                    return {}

                return {
                    'status': 'ok',
                    'notificacoes_endividamento_pendentes': notif_endividamento_pendentes,
                    'endividamentos_ativos': endividamentos_ativos,
                    'documentos_vencimento_proximo': docs_vencimento_proximo,
                    'documentos_vencidos': docs_vencidos,
                    'query_time': round(query_time, 3),
                    'timestamp': datetime.now().isoformat(),
                    'celery_status': 'active',
                    'memoria_db': obter_status_banco_dados()
                }
        except Exception as e:
            logger.error(f"Erro no teste de notificações: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    @celery.task(
        name='tasks.limpar_notificacoes_antigas',
        bind=True,
        rate_limit='1/h'
    )
    def limpar_notificacoes_antigas(self, dias: int = 90) -> Dict[str, Any]:
        """
        Remove notificações antigas já processadas
        """
        from src.models.notificacao_endividamento import HistoricoNotificacao, NotificacaoEndividamento
        from src.models.db import db

        try:
            with current_app.app_context():
                task_id = self.request.id or 'task-no-id'
                logger.info(f"[{task_id}] Iniciando limpeza de notificações antigas (>{dias} dias)")

                data_limite = datetime.now() - timedelta(days=dias)
                stats = {'historico': 0, 'notificacoes': 0}

                # 1. Limpar histórico antigo
                try:
                    total_historico = HistoricoNotificacao.query.filter(
                        HistoricoNotificacao.data_envio < data_limite
                    ).count()

                    if total_historico > 0:
                        batch_size = 1000
                        deletados = 0
                        while True:
                            batch = HistoricoNotificacao.query.filter(
                                HistoricoNotificacao.data_envio < data_limite
                            ).limit(batch_size).all()
                            if not batch:
                                break
                            for item in batch:
                                db.session.delete(item)
                            db.session.commit()
                            deletados += len(batch)
                            logger.info(f"Deletados {deletados}/{total_historico} registros de histórico...")
                        stats['historico'] = deletados
                except Exception as e:
                    logger.error(f"Erro ao limpar histórico: {e}")
                    db.session.rollback()

                # 2. Limpar notificações antigas enviadas
                try:
                    total_notificacoes = NotificacaoEndividamento.query.filter(
                        and_(
                            NotificacaoEndividamento.data_envio < data_limite,
                            NotificacaoEndividamento.enviado == True,
                            NotificacaoEndividamento.tipo_notificacao != 'config'
                        )
                    ).count()

                    if total_notificacoes > 0:
                        batch_size = 1000
                        deletados = 0
                        while True:
                            batch = NotificacaoEndividamento.query.filter(
                                and_(
                                    NotificacaoEndividamento.data_envio < data_limite,
                                    NotificacaoEndividamento.enviado == True,
                                    NotificacaoEndividamento.tipo_notificacao != 'config'
                                )
                            ).limit(batch_size).all()
                            if not batch:
                                break
                            for item in batch:
                                db.session.delete(item)
                            db.session.commit()
                            deletados += len(batch)
                            logger.info(f"Deletados {deletados}/{total_notificacoes} registros de notificações...")
                        stats['notificacoes'] = deletados
                except Exception as e:
                    logger.error(f"Erro ao limpar notificações: {e}")
                    db.session.rollback()

                total_deletados = stats['historico'] + stats['notificacoes']

                logger.info(
                    f"[{task_id}] Limpeza concluída. "
                    f"Removidos {total_deletados} registros antigos "
                    f"({stats['historico']} histórico, {stats['notificacoes']} notificações)"
                )

                return {
                    'status': 'success',
                    'stats': stats,
                    'total_deletados': total_deletados,
                    'timestamp': datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(
                f"[{self.request.id}] Erro ao limpar notificações antigas: {e}",
                exc_info=True
            )
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    @celery.task(
        name='tasks.test_celery',
        time_limit=10
    )
    def test_celery() -> Dict[str, str]:
        """
        Tarefa simples para testar se o Celery está funcionando
        """
        return {
            'status': 'ok',
            'message': 'Celery está funcionando!',
            'timestamp': datetime.now().isoformat(),
            'worker': celery.current_task.request.hostname
        }

    global celery_tasks
    celery_tasks = {
        'processar_notificacoes_endividamento': processar_notificacoes_endividamento,
        'processar_notificacoes_documentos': processar_notificacoes_documentos,
        'processar_todas_notificacoes': processar_todas_notificacoes,
        'test_notificacoes': test_notificacoes,
        'limpar_notificacoes_antigas': limpar_notificacoes_antigas,
        'test_celery': test_celery
    }

    return celery_tasks


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