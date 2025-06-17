from flask_login import current_user
from flask import request
from src.models.audit_log import AuditLog
from src.models.db import db

def log_audit(action, details=None):
    user_id = getattr(current_user, 'id', None)
    username = getattr(current_user, 'nome', None) or getattr(current_user, 'email', None)
    ip = request.remote_addr
    log = AuditLog(
        user_id=user_id,
        username=username,
        action=action,
        details=details,
        ip=ip
    )
    db.session.add(log)
    db.session.commit()