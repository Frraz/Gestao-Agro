# /src/celery_config.py
"""
Configuração unificada do Celery para o sistema Gestão Agro
Este arquivo centraliza todas as configurações do Celery e Celery Beat
"""
import os
import logging
from typing import Optional, Dict, Any
from celery import Celery, Task
from celery.schedules import crontab
from datetime import timedelta
from kombu import Queue, Exchange

logger = logging.getLogger(__name__)

# Configurações padrão
DEFAULT_BROKER_URL = 'redis://localhost:6379/0'
DEFAULT_TIMEZONE = 'America/Sao_Paulo'


class FlaskTask(Task):
    """
    Classe base para tarefas que precisam do contexto Flask
    """
    abstract = True
    _app = None

    @property
    def app(self):
        return self._app

    def __call__(self, *args, **kwargs):
        if self.app:
            with self.app.app_context():
                return self.run(*args, **kwargs)
        return self.run(*args, **kwargs)


def make_celery(app=None) -> Celery:
    """
    Cria e configura instância do Celery
    
    Args:
        app: Instância do Flask (opcional)
        
    Returns:
        Instância configurada do Celery
    """
    
    # URLs de conexão
    broker_url = os.environ.get('CELERY_BROKER_URL') or \
                 os.environ.get('REDIS_URL') or \
                 DEFAULT_BROKER_URL
    
    result_backend = os.environ.get('CELERY_RESULT_BACKEND') or \
                     os.environ.get('REDIS_URL') or \
                     broker_url
    
    # Criar instância do Celery
    celery_app = Celery(
        'gestao-agro',
        broker=broker_url,
        backend=result_backend,
        include=[
            'src.utils.tasks_notificacao',
            'src.utils.tasks'
        ]
    )
    
    # ========== CONFIGURAÇÕES BASE ==========
    celery_app.conf.update(
        # Serialização
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        
        # Timezone
        timezone=DEFAULT_TIMEZONE,
        enable_utc=True,
        
        # Expiração e limites
        result_expires=3600,  # 1 hora
        task_track_started=True,
        task_send_sent_event=True,
        task_time_limit=600,  # 10 minutos hard limit
        task_soft_time_limit=300,  # 5 minutos soft limit
        task_acks_late=True,  # Importante para confiabilidade
        
        # Worker
        worker_prefetch_multiplier=1,  # Importante para tarefas longas
        worker_max_tasks_per_child=1000,  # Reinicia worker após 1000 tarefas
        worker_disable_rate_limits=False,
        worker_hijack_root_logger=False,  # Não sobrescrever nosso logger
        
        # Pool de conexões
        broker_pool_limit=10,
        broker_connection_retry=True,
        broker_connection_retry_on_startup=True,
        broker_connection_max_retries=10,
        
        # Redis específico
        redis_max_connections=20,
        redis_socket_keepalive=True,
        redis_socket_keepalive_options={},
        redis_retry_on_timeout=True,
        
        # Resultado backend
        result_backend_transport_options={
            'master_name': 'mymaster',
            'visibility_timeout': 3600,
            'fanout_prefix': True,
            'fanout_patterns': True
        },
        
        # Roteamento de tarefas
        task_routes={
            'tasks.processar_notificacoes_endividamento': {'queue': 'notifications'},
            'tasks.processar_notificacoes_documentos': {'queue': 'notifications'},
            'tasks.processar_todas_notificacoes': {'queue': 'notifications'},
            'tasks.limpar_notificacoes_antigas': {'queue': 'maintenance'},
            'tasks.test_*': {'queue': 'default'},
        },
        
        # Filas
        task_queues=(
            Queue('default', Exchange('default'), routing_key='default'),
            Queue('notifications', Exchange('notifications'), routing_key='notifications', priority=10),
            Queue('maintenance', Exchange('maintenance'), routing_key='maintenance', priority=1),
        ),
        
        # Prioridade padrão
        task_default_priority=5,
        task_inherit_parent_priority=True,
        
        # ========== BEAT SCHEDULE (AGENDAMENTO) ==========
        beat_schedule={
            # Verificação frequente (a cada 5 minutos)
            'verificar-notificacoes-periodicamente': {
                'task': 'tasks.processar_todas_notificacoes',
                'schedule': timedelta(minutes=5),
                'options': {
                    'queue': 'notifications',
                    'priority': 5,
                    'expires': 300,  # Expira em 5 minutos
                    'time_limit': 180,  # Limite de 3 minutos
                }
            },
            
            # Verificação matinal (8h da manhã)
            'verificacao-matinal': {
                'task': 'tasks.processar_todas_notificacoes',
                'schedule': crontab(hour=8, minute=0),
                'options': {
                    'queue': 'notifications',
                    'priority': 10,
                    'expires': 3600,
                }
            },
            
            # Verificação vespertina (14h)
            'verificacao-vespertina': {
                'task': 'tasks.processar_todas_notificacoes',
                'schedule': crontab(hour=14, minute=0),
                'options': {
                    'queue': 'notifications',
                    'priority': 10,
                    'expires': 3600,
                }
            },
            
            # Verificação noturna (20h - último aviso do dia)
            'verificacao-noturna': {
                'task': 'tasks.processar_todas_notificacoes',
                'schedule': crontab(hour=20, minute=0),
                'options': {
                    'queue': 'notifications',
                    'priority': 10,
                    'expires': 3600,
                }
            },
            
            # Limpeza de notificações antigas (2h da manhã)
            'limpar-notificacoes-antigas': {
                'task': 'tasks.limpar_notificacoes_antigas',
                'schedule': crontab(hour=2, minute=0),
                'kwargs': {'dias': 90},
                'options': {
                    'queue': 'maintenance',
                    'priority': 1,
                    'expires': 7200,
                }
            },
            
            # Health check do sistema (a cada 10 minutos)
            'health-check-celery': {
                'task': 'tasks.test_celery',
                'schedule': timedelta(minutes=10),
                'options': {
                    'queue': 'default',
                    'priority': 1,
                    'expires': 600,
                    'time_limit': 30,
                }
            },
        },
        
        # Configurações do Beat
        beat_scheduler='celery.beat:PersistentScheduler',
        beat_schedule_filename='celerybeat-schedule.db',
        beat_sync_every=10,  # Sincroniza a cada 10 batidas
        beat_max_loop_interval=5,  # Intervalo máximo de 5 segundos
    )
    
    # Configurações específicas para desenvolvimento
    if os.environ.get('FLASK_ENV') == 'development':
        celery_app.conf.update(
            task_always_eager=False,  # Manter False mesmo em dev para testar Celery real
            task_eager_propagates=True,
            worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
            worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s',
            
            # Em dev, verificar notificações mais frequentemente
            beat_schedule={
                **celery_app.conf.beat_schedule,
                'verificar-notificacoes-dev': {
                    'task': 'tasks.processar_todas_notificacoes',
                    'schedule': timedelta(minutes=1),
                    'options': {
                        'queue': 'notifications',
                        'priority': 10,
                        'expires': 60,
                    }
                },
            }
        )
    
    # Configurações específicas para testes
    if os.environ.get('FLASK_ENV') == 'testing':
        celery_app.conf.update(
            task_always_eager=True,
            task_eager_propagates=True,
            broker_url='memory://',
            result_backend='cache+memory://',
        )
    
    # Se temos uma app Flask, configurar integração
    if app:
        # Atualizar com configurações do Flask
        celery_app.conf.update(
            broker_url=app.config.get('CELERY_BROKER_URL', broker_url),
            result_backend=app.config.get('CELERY_RESULT_BACKEND', result_backend),
        )
        
        # Sobrescrever outras configurações do Flask se existirem
        for key in app.config:
            if key.startswith('CELERY_'):
                celery_app.conf[key.lower().replace('celery_', '')] = app.config[key]
        
        # Configurar classe de tarefa com contexto Flask
        FlaskTask._app = app
        celery_app.Task = FlaskTask
        
        # Log de confirmação
        logger.info(f"Celery configurado com broker: {celery_app.conf.broker_url}")
        logger.info(f"Timezone: {celery_app.conf.timezone}")
        logger.info(f"Total de tarefas agendadas: {len(celery_app.conf.beat_schedule)}")
    
    return celery_app


def init_celery(app) -> Celery:
    """
    Inicializa Celery com contexto Flask
    Função alternativa para usar em factory pattern
    
    Args:
        app: Instância do Flask
        
    Returns:
        Instância configurada do Celery
    """
    celery = make_celery(app)
    app.celery = celery
    return celery


# Instância global do Celery (será atualizada com contexto Flask quando app inicializar)
celery = make_celery()

# Configuração para Celery Beat standalone
beat_app = make_celery()


# Funções utilitárias
def get_task_info(task_id: str) -> Dict[str, Any]:
    """Obtém informações sobre uma tarefa"""
    from celery.result import AsyncResult
    
    result = AsyncResult(task_id, app=celery)
    return {
        'task_id': task_id,
        'state': result.state,
        'current': result.info.get('current', 0) if isinstance(result.info, dict) else 0,
        'total': result.info.get('total', 1) if isinstance(result.info, dict) else 1,
        'status': result.info.get('status', '') if isinstance(result.info, dict) else str(result.info),
        'result': result.result if result.state == 'SUCCESS' else None,
        'traceback': result.traceback if result.state == 'FAILURE' else None,
    }


def purge_all_tasks():
    """Remove todas as tarefas pendentes (usar com cuidado!)"""
    celery.control.purge()
    logger.warning("Todas as tarefas pendentes foram removidas!")


def get_active_queues() -> Dict[str, int]:
    """Retorna o número de tarefas em cada fila"""
    i = celery.control.inspect()
    active = i.active()
    reserved = i.reserved()
    
    queues = {}
    
    if active:
        for worker, tasks in active.items():
            for task in tasks:
                queue = task.get('delivery_info', {}).get('routing_key', 'default')
                queues[queue] = queues.get(queue, 0) + 1
    
    if reserved:
        for worker, tasks in reserved.items():
            for task in tasks:
                queue = task.get('delivery_info', {}).get('routing_key', 'default')
                queues[queue] = queues.get(queue, 0) + 1
    
    return queues