# /src/uils/auditoria.py

import json
from datetime import datetime

from flask_login import current_user

from src.models.auditoria import Auditoria
from src.models.db import db


def registrar_auditoria(acao, entidade, valor_anterior=None, valor_novo=None):
    usuario_id = getattr(current_user, "id", None)
    log = Auditoria(
        usuario_id=usuario_id,
        acao=acao,
        entidade=entidade,
        valor_anterior=json.dumps(valor_anterior) if valor_anterior else None,
        valor_novo=json.dumps(valor_novo) if valor_novo else None,
        data_hora=datetime.utcnow(),
    )
    db.session.add(log)
    db.session.commit()
