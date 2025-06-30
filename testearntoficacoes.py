# testearntoficacoes.py

from src.main import create_app
from src.utils.tasks_notificacao import processar_notificacoes_documentos

app = create_app()
with app.app_context():
    enviados = processar_notificacoes_documentos()
    print(f"Foram enviados {enviados} e-mail(s) de notificação automática.")