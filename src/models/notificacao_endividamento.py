# /src/models/notificacao_endividamento.py

"""
Modelos para notificações e histórico de notificações de endividamento.

Inclui:
- NotificacaoEndividamento: Notificações ativas associadas a um endividamento.
- HistoricoNotificacao: Armazena envios realizados e status de notificações.
"""

import json
from datetime import datetime
from typing import Optional

from src.models.db import db

class NotificacaoEndividamento(db.Model):
    """
    Modelo para notificações de endividamento.
    """

    __tablename__ = "notificacao_endividamento"

    id = db.Column(db.Integer, primary_key=True)
    endividamento_id = db.Column(
        db.Integer, db.ForeignKey("endividamento.id", ondelete="CASCADE"), nullable=False, index=True
    )
    emails = db.Column(db.Text, nullable=False)  # JSON string com lista de emails
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    endividamento = db.relationship("Endividamento", back_populates="notificacoes", lazy="joined")

    def __repr__(self) -> str:
        return f"<NotificacaoEndividamento {self.endividamento_id}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "endividamento_id": self.endividamento_id,
            "emails": json.loads(self.emails) if self.emails else [],
            "ativo": self.ativo,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class HistoricoNotificacao(db.Model):
    """
    Modelo para histórico de notificações enviadas.
    """

    __tablename__ = "historico_notificacao"

    id = db.Column(db.Integer, primary_key=True)
    endividamento_id = db.Column(
        db.Integer, db.ForeignKey("endividamento.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tipo_notificacao = db.Column(
        db.String(20), nullable=False, index=True
    )  # '6_meses', '3_meses', '30_dias', etc.
    data_envio = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    emails_enviados = db.Column(
        db.Text, nullable=False
    )  # JSON string com lista de emails
    sucesso = db.Column(db.Boolean, default=True)
    erro_mensagem = db.Column(db.Text, nullable=True)

    endividamento = db.relationship("Endividamento", lazy="joined")

    def __repr__(self) -> str:
        return (
            f"<HistoricoNotificacao {self.endividamento_id} - {self.tipo_notificacao}>"
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "endividamento_id": self.endividamento_id,
            "tipo_notificacao": self.tipo_notificacao,
            "data_envio": self.data_envio.isoformat() if self.data_envio else None,
            "emails_enviados": (
                json.loads(self.emails_enviados) if self.emails_enviados else []
            ),
            "sucesso": self.sucesso,
            "erro_mensagem": self.erro_mensagem,
        }