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
celery.conf.enable_utc = False

# Agendamento das notificações para 08:00 da manhã todos os dias
celery.conf.beat_schedule = {
    "verificar-notificacoes-documentos": {
        "task": "src.utils.notificacao_documentos_service.verificar_e_enviar_notificacoes_task",
        "schedule": crontab(hour=8, minute=0),
    },
    "verificar-notificacoes-endividamento": {
        "task": "src.utils.notificacao_endividamento_service.verificar_e_enviar_notificacoes_task",
        "schedule": crontab(hour=8, minute=0),
    },
    # Adicione outras tasks recorrentes aqui, se necessário
}

if __name__ == '__main__':
    celery.start()