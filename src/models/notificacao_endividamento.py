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


class NotificacaoEndividamento(db.Model):  # type: ignore
    """
    Modelo para notificações de endividamento.
    """

    __tablename__ = "notificacao_endividamento"

    id: int = db.Column(db.Integer, primary_key=True)
    endividamento_id: int = db.Column(
        db.Integer, db.ForeignKey("endividamento.id"), nullable=False
    )
    emails: str = db.Column(db.Text, nullable=False)  # JSON string com lista de emails
    ativo: bool = db.Column(db.Boolean, default=True)
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at: datetime = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    endividamento = db.relationship("Endividamento", back_populates="notificacoes")

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


class HistoricoNotificacao(db.Model):  # type: ignore
    """
    Modelo para histórico de notificações enviadas.
    """

    __tablename__ = "historico_notificacao"

    id: int = db.Column(db.Integer, primary_key=True)
    endividamento_id: int = db.Column(
        db.Integer, db.ForeignKey("endividamento.id"), nullable=False
    )
    tipo_notificacao: str = db.Column(
        db.String(20), nullable=False
    )  # '6_meses', '3_meses', '30_dias', etc.
    data_envio: datetime = db.Column(db.DateTime, default=datetime.utcnow)
    emails_enviados: str = db.Column(
        db.Text, nullable=False
    )  # JSON string com lista de emails
    sucesso: bool = db.Column(db.Boolean, default=True)
    erro_mensagem: Optional[str] = db.Column(db.Text, nullable=True)

    endividamento = db.relationship("Endividamento")

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