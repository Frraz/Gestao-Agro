# /celery_app.py

"""
Arquivo de entrada para o Celery Worker e Beat
Configura agendamento das tarefas de notificação para 08:00 (horário de Brasília)
"""

import os
import sys

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from celery.schedules import crontab
from src.main import celery  # Importa APENAS o celery, não a app

# Configuração de timezone
celery.conf.timezone = "America/Sao_Paulo"
celery.conf.enable_utc = True  # Usar UTC internamente, mas converter para timezone local

# Agendamento das notificações para 08:00 da manhã todos os dias
celery.conf.beat_schedule = {
    "verificar-notificacoes-documentos": {
        "task": "tasks.processar_notificacoes_documentos",
        "schedule": crontab(hour=8, minute=0),
    },
    "verificar-notificacoes-endividamento": {
        "task": "tasks.processar_notificacoes_endividamento",
        "schedule": crontab(hour=8, minute=0),
    },
    "verificar-todas-notificacoes": {
        "task": "tasks.processar_todas_notificacoes",
        "schedule": crontab(hour=8, minute=0),
    },
    # Verificação adicional às 14h
    "verificar-todas-notificacoes-vespertino": {
        "task": "tasks.processar_todas_notificacoes",
        "schedule": crontab(hour=14, minute=0),
    },
    # Teste de conectividade a cada 5 minutos (apenas em desenvolvimento)
    "teste-sistema-notificacoes": {
        "task": "tasks.test_notificacoes",
        "schedule": crontab(minute="*/5"),  # A cada 5 minutos
    },
    # Adicione outras tasks recorrentes aqui, se necessário
}

if __name__ == '__main__':
    celery.start()