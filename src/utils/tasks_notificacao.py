# /src/utils/tasks_notificacao.py

"""
Tarefas agendadas para notificações via Celery
Define jobs para processamento assíncrono de notificações de documentos e endividamentos
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union

from celery import Task, signature
from flask import current_app
from sqlalchemy import and_, or_

logger = logging.getLogger(__name__)

# Variável para armazenar as tarefas do Celery
celery_tasks = {}


def criar_tarefas_notificacao(celery) -> Dict[str, Any]:
    """
    Cria e registra as tarefas de notificação no Celery
    
    Args:
        celery: Instância do Celery
        
    Returns:
        Dicionário com as tarefas registradas
    """
    
    @celery.task(
        name='tasks.processar_notificacoes_endividamento',
        bind=True,
        max_retries=3,
        soft_time_limit=300,  # 5 minutos soft limit
        time_limit=600,       # 10 minutos hard limit
        rate_limit='100/m'    # Max 100 execuções por minuto
    )
    def processar_notificacoes_endividamento(self) -> Dict[str, Any]:
        """
        Tarefa agendada para processar notificações de endividamento
        
        Returns:
            Dicionário com resultados do processamento
        """
        from src.utils.notificacao_endividamento_service import notificacao_endividamento_service
        
        try:
            with current_app.app_context():
                start_time = datetime.now()
                task_id = self.request.id or 'task-no-id'
                
                logger.info(
                    f"[{task_id}] Iniciando processamento de notificações de endividamento - {start_time}"
                )
                
                # Executar serviço de notificações
                notificacoes_enviadas = notificacao_endividamento_service.verificar_e_enviar_notificacoes()
                
                # Calcular duração
                duration = (datetime.now() - start_time).total_seconds()
                
                # Registrar informações de performance
                if duration > 60:  # Alerta se demorar mais de 1 minuto
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
            # Retry com backoff exponencial
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

    @celery.task(
        name='tasks.processar_notificacoes_documentos',
        bind=True,
        max_retries=3,
        soft_time_limit=300,
        time_limit=600,
        rate_limit='100/m'
    )
    def processar_notificacoes_documentos(self) -> Dict[str, Any]:
        """
        Tarefa agendada para processar notificações de documentos
        
        Returns:
            Dicionário com resultados do processamento
        """
        from src.utils.notificacao_documentos_service import notificacao_documento_service
        
        try:
            with current_app.app_context():
                start_time = datetime.now()
                task_id = self.request.id or 'task-no-id'
                
                logger.info(
                    f"[{task_id}] Iniciando processamento de notificações de documentos - {start_time}"
                )
                
                # Executar serviço de notificações
                notificacoes_enviadas = notificacao_documento_service.verificar_e_enviar_notificacoes()
                
                # Calcular duração
                duration = (datetime.now() - start_time).total_seconds()
                
                # Registrar informações de performance
                if duration > 60:  # Alerta se demorar mais de 1 minuto
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
        
        Returns:
            Dicionário com resultados consolidados
        """
        try:
            with current_app.app_context():
                start_time = datetime.now()
                task_id = self.request.id or 'task-no-id'
                
                logger.info(
                    f"[{task_id}] === INICIANDO PROCESSAMENTO DE TODAS AS NOTIFICAÇÕES ==="
                )
                
                # Registrar métricas de início
                try:
                    _registrar_metricas_inicio_processamento()
                except Exception as e:
                    logger.error(f"Erro ao registrar métricas de início: {e}")
                
                # Processar notificações de endividamento com timeout
                try:
                    resultado_endividamento = processar_notificacoes_endividamento.apply_async().get(timeout=300)
                except Exception as e:
                    logger.error(f"Erro em notificações de endividamento: {e}")
                    resultado_endividamento = {
                        'notificacoes_enviadas': 0,
                        'status': 'error',
                        'error': str(e)
                    }
                
                # Processar notificações de documentos com timeout
                try:
                    resultado_documentos = processar_notificacoes_documentos.apply_async().get(timeout=300)
                except Exception as e:
                    logger.error(f"Erro em notificações de documentos: {e}")
                    resultado_documentos = {
                        'notificacoes_enviadas': 0,
                        'status': 'error',
                        'error': str(e)
                    }
                
                # Calcular totais
                total_enviadas = (
                    resultado_endividamento.get('notificacoes_enviadas', 0) +
                    resultado_documentos.get('notificacoes_enviadas', 0)
                )
                
                duration = (datetime.now() - start_time).total_seconds()
                
                # Registrar métricas de conclusão
                try:
                    _registrar_metricas_conclusao_processamento(
                        total_enviadas=total_enviadas, 
                        duracao=duration
                    )
                except Exception as e:
                    logger.error(f"Erro ao registrar métricas de conclusão: {e}")
                
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
        time_limit=30  # 30 segundos no máximo para diagnóstico
    )
    def test_notificacoes() -> Dict[str, Any]:
        """
        Testa se o sistema de notificações está acessível
        
        Returns:
            Dicionário com informações de diagnóstico
        """
        try:
            with current_app.app_context():
                from src.models.notificacao_endividamento import NotificacaoEndividamento
                from src.models.endividamento import Endividamento
                from src.models.documento import Documento
                
                start_time = time.time()
                
                # Conta notificações pendentes de endividamento (excluindo configurações)
                notif_endividamento_pendentes = NotificacaoEndividamento.query.filter(
                    NotificacaoEndividamento.ativo == True,
                    NotificacaoEndividamento.enviado == False,
                    NotificacaoEndividamento.tipo_notificacao != 'config',
                    NotificacaoEndividamento.data_envio <= datetime.utcnow()
                ).count()
                
                # Conta endividamentos ativos
                endividamentos_ativos = Endividamento.query.filter(
                    Endividamento.data_vencimento_final > datetime.now().date()
                ).count()
                
                # Conta documentos com vencimento próximo (30 dias)
                data_limite = datetime.now().date() + timedelta(days=30)
                docs_vencimento_proximo = Documento.query.filter(
                    and_(
                        Documento.data_vencimento.isnot(None),
                        Documento.data_vencimento <= data_limite,
                        Documento.data_vencimento >= datetime.now().date()
                    )
                ).count()
                
                # Conta documentos vencidos
                docs_vencidos = Documento.query.filter(
                    and_(
                        Documento.data_vencimento.isnot(None),
                        Documento.data_vencimento < datetime.now().date()
                    )
                ).count()
                
                # Medir tempo de resposta
                query_time = time.time() - start_time
                
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
        rate_limit='1/h'  # Máximo 1 vez por hora
    )
    def limpar_notificacoes_antigas(self, dias: int = 90) -> Dict[str, Any]:
        """
        Remove notificações antigas já processadas
        
        Args:
            dias: Idade em dias para considerar um registro como antigo
            
        Returns:
            Dicionário com resultado da operação
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
                    # Contar antes de deletar
                    total_historico = HistoricoNotificacao.query.filter(
                        HistoricoNotificacao.data_envio < data_limite
                    ).count()
                    
                    if total_historico > 0:
                        # Deletar em lotes para evitar timeout
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
                    # Contar antes de deletar
                    total_notificacoes = NotificacaoEndividamento.query.filter(
                        and_(
                            NotificacaoEndividamento.data_envio < data_limite,
                            NotificacaoEndividamento.enviado == True,
                            NotificacaoEndividamento.tipo_notificacao != 'config'
                        )
                    ).count()
                    
                    if total_notificacoes > 0:
                        # Deletar em lotes para evitar timeout
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
        
        Returns:
            Dicionário com informações do worker
        """
        return {
            'status': 'ok',
            'message': 'Celery está funcionando!',
            'timestamp': datetime.now().isoformat(),
            'worker': celery.current_task.request.hostname
        }

    # Armazenar referências das tarefas
    global celery_tasks
    celery_tasks = {
        'processar_notificacoes_endividamento': processar_notificacoes_endividamento,
        'processar_notificacoes_documentos': processar_notificacoes_documentos,
        'processar_todas_notificacoes': processar_todas_notificacoes,
        'test_notificacoes': test_notificacoes,
        'limpar_notificacoes_antigas': limpar_notificacoes_antigas,
        'test_celery': test_celery
    }
    
    logger.info(f"Tarefas de notificação registradas: {list(celery_tasks.keys())}")
    
    return celery_tasks


# Funções auxiliares para execução direta (sem Celery)
def processar_notificacoes_endividamento_sync() -> int:
    """
    Executa diretamente o serviço de notificações de endividamento
    
    Returns:
        Número de notificações enviadas
    """
    from src.utils.notificacao_endividamento_service import notificacao_endividamento_service
    return notificacao_endividamento_service.verificar_e_enviar_notificacoes()


def processar_notificacoes_documentos_sync() -> int:
    """
    Executa diretamente o serviço de notificações de documentos
    
    Returns:
        Número de notificações enviadas
    """
    from src.utils.notificacao_documentos_service import notificacao_documento_service
    return notificacao_documento_service.verificar_e_enviar_notificacoes()


def processar_todas_notificacoes_sync() -> Dict[str, Any]:
    """
    Executa todas as notificações sincronamente
    
    Returns:
        Dicionário com resultados do processamento
    """
    try:
        start_time = datetime.now()
        
        notif_endividamento = processar_notificacoes_endividamento_sync()
        notif_documentos = processar_notificacoes_documentos_sync()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return {
            'status': 'success',
            'endividamento': notif_endividamento,
            'documentos': notif_documentos,
            'total': notif_endividamento + notif_documentos,
            'duration_seconds': duration,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Erro ao processar notificações sincronamente: {e}", exc_info=True)
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


def agendar_proxima_execucao(app=None) -> Dict[str, Any]:
    """
    Agenda as próximas execuções das tarefas de notificação
    
    Args:
        app: Aplicação Flask (opcional)
        
    Returns:
        Dicionário com IDs das tarefas agendadas
    """
    try:
        if not celery_tasks:
            logger.error("Tarefas Celery não foram inicializadas")
            return {'status': 'error', 'message': 'Tarefas não inicializadas'}
        
        # Determinar horários de execução
        agora = datetime.now()
        proxima_execucao_documentos = None
        proxima_execucao_endividamentos = None
        
        # Tentar agendar as tarefas
        try:
            # Horário para notificações de documentos (duas vezes ao dia)
            hora_documentos_manha = 9  # 9:00 da manhã
            hora_documentos_tarde = 15  # 15:00 da tarde
            
            if agora.hour < hora_documentos_manha:
                # Agendar para hoje de manhã
                proxima_execucao_documentos = agora.replace(
                    hour=hora_documentos_manha, minute=0, second=0, microsecond=0
                )
            elif agora.hour < hora_documentos_tarde:
                # Agendar para hoje à tarde
                proxima_execucao_documentos = agora.replace(
                    hour=hora_documentos_tarde, minute=0, second=0, microsecond=0
                )
            else:
                # Agendar para amanhã de manhã
                proxima_execucao_documentos = agora.replace(
                    hour=hora_documentos_manha, minute=0, second=0, microsecond=0
                ) + timedelta(days=1)
            
            # Horário para notificações de endividamentos (uma vez ao dia)
            hora_endividamentos = 10  # 10:00 da manhã
            
            if agora.hour < hora_endividamentos:
                # Agendar para hoje
                proxima_execucao_endividamentos = agora.replace(
                    hour=hora_endividamentos, minute=0, second=0, microsecond=0
                )
            else:
                # Agendar para amanhã
                proxima_execucao_endividamentos = agora.replace(
                    hour=hora_endividamentos, minute=0, second=0, microsecond=0
                ) + timedelta(days=1)
                
            # Agendar tarefas
            task_ids = {}
            
            # Documentos
            if proxima_execucao_documentos:
                task = celery_tasks['processar_notificacoes_documentos'].apply_async(
                    eta=proxima_execucao_documentos
                )
                task_ids['documentos'] = task.id
                
            # Endividamentos
            if proxima_execucao_endividamentos:
                task = celery_tasks['processar_notificacoes_endividamento'].apply_async(
                    eta=proxima_execucao_endividamentos
                )
                task_ids['endividamentos'] = task.id
                
            # Limpeza semanal (domingo às 03:00)
            if agora.weekday() == 6:  # Domingo
                task = celery_tasks['limpar_notificacoes_antigas'].apply_async(
                    kwargs={'dias': 90},
                    eta=agora.replace(hour=3, minute=0, second=0, microsecond=0)
                )
                task_ids['limpeza'] = task.id
                
            logger.info(
                f"Próximas execuções agendadas: "
                f"Documentos: {proxima_execucao_documentos}, "
                f"Endividamentos: {proxima_execucao_endividamentos}"
            )
                
            return {
                'status': 'success',
                'proxima_execucao_documentos': proxima_execucao_documentos.isoformat() if proxima_execucao_documentos else None,
                'proxima_execucao_endividamentos': proxima_execucao_endividamentos.isoformat() if proxima_execucao_endividamentos else None,
                'task_ids': task_ids
            }
                
        except Exception as e:
            logger.error(f"Erro ao agendar próxima execução: {e}", exc_info=True)
            return {'status': 'error', 'error': str(e)}
            
    except Exception as e:
        logger.error(f"Erro geral ao agendar tarefas: {e}", exc_info=True)
        return {'status': 'error', 'error': str(e)}


def obter_status_banco_dados() -> Dict[str, Any]:
    """
    Obtém informações sobre o status do banco de dados
    
    Returns:
        Dicionário com informações de status
    """
    try:
        from src.models.db import db
        from sqlalchemy import text
        
        status = {'tabelas': {}}
        
        # SQLite: Verifica espaço usado
        try:
            if 'sqlite' in db.engine.url.drivername:
                result = db.session.execute(text("PRAGMA page_count, page_size")).fetchone()
                if result:
                    page_count, page_size = result
                    size_bytes = page_count * page_size
                    status['tamanho_db'] = size_bytes
                    status['tamanho_mb'] = round(size_bytes / (1024 * 1024), 2)
        except Exception as e:
            logger.debug(f"Não foi possível obter tamanho do SQLite: {e}")
        
        # Contar registros nas tabelas principais
        try:
            tabelas = [
                'documento',
                'notificacao_endividamento',
                'historico_notificacao',
                'endividamento'
            ]
            
            for tabela in tabelas:
                try:
                    result = db.session.execute(text(f"SELECT COUNT(*) FROM {tabela}")).scalar()
                    status['tabelas'][tabela] = result
                except Exception as e:
                    status['tabelas'][tabela] = f"erro: {str(e)}"
        except Exception as e:
            logger.debug(f"Erro ao contar registros: {e}")
        
        return status
        
    except Exception as e:
        logger.error(f"Erro ao obter status do banco: {e}")
        return {'error': str(e)}


def _registrar_metricas_inicio_processamento() -> None:
    """Registra métricas no início do processamento de notificações"""
    try:
        from src.models.documento import Documento
        from src.models.endividamento import Endividamento
        from src.models.notificacao_endividamento import NotificacaoEndividamento
        
        hoje = datetime.now().date()
        
        # Contar notificações pendentes
        pendentes = NotificacaoEndividamento.query.filter(
            NotificacaoEndividamento.ativo == True,
            NotificacaoEndividamento.enviado == False,
            NotificacaoEndividamento.tipo_notificacao != 'config'
        ).count()
        
        # Contar documentos vencendo em 7 dias
        docs_7dias = Documento.query.filter(
            Documento.data_vencimento.isnot(None),
            Documento.data_vencimento <= hoje + timedelta(days=7),
            Documento.data_vencimento >= hoje
        ).count()
        
        # Contar endividamentos vencendo em 7 dias
        endiv_7dias = Endividamento.query.filter(
            Endividamento.data_vencimento_final <= hoje + timedelta(days=7),
            Endividamento.data_vencimento_final >= hoje
        ).count()
        
        logger.info(
            f"MÉTRICAS INICIAIS: "
            f"{pendentes} notificações pendentes, "
            f"{docs_7dias} documentos vencendo em 7 dias, "
            f"{endiv_7dias} endividamentos vencendo em 7 dias"
        )
    except Exception as e:
        logger.error(f"Erro ao registrar métricas iniciais: {e}")


def _registrar_metricas_conclusao_processamento(total_enviadas: int, duracao: float) -> None:
    """
    Registra métricas ao final do processamento
    
    Args:
        total_enviadas: Total de notificações enviadas
        duracao: Tempo total de processamento em segundos
    """
    try:
        # Registrar no log
        if total_enviadas > 0:
            tempo_medio = duracao / total_enviadas if total_enviadas > 0 else 0
            logger.info(
                f"MÉTRICAS FINAIS: "
                f"{total_enviadas} notificações enviadas, "
                f"duração total: {duracao:.2f}s, "
                f"tempo médio: {tempo_medio:.2f}s por notificação"
            )
        else:
            logger.info(
                f"MÉTRICAS FINAIS: "
                f"Nenhuma notificação enviada, "
                f"duração total: {duracao:.2f}s"
            )
    except Exception as e:
        logger.error(f"Erro ao registrar métricas finais: {e}")