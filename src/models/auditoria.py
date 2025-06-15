from datetime import datetime
from src.models.db import db

class Auditoria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)
    acao = db.Column(db.String(100), nullable=False)
    entidade = db.Column(db.String(100), nullable=False)
    valor_anterior = db.Column(db.Text, nullable=True)
    valor_novo = db.Column(db.Text, nullable=True)
    data_hora = db.Column(db.DateTime, default=datetime.utcnow)

    usuario = db.relationship('Usuario')