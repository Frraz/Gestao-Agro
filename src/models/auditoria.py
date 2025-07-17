# /src/models/auditoria.py

"""
Modelo unificado de auditoria para registrar ações e alterações no sistema.

Este modelo cobre tanto logs gerais de eventos (login, operações administrativas, etc.)
quanto logs de alterações de entidades, registrando valores anteriores e novos quando aplicável.
"""

from datetime import datetime
from typing import Optional

from src.models.db import db

class Auditoria(db.Model):
    """
    Modelo unificado de auditoria do sistema.

    Attributes:
        id (int): Identificador único do registro de auditoria.
        usuario_id (Optional[int]): ID do usuário responsável pela ação.
        username (Optional[str]): Nome do usuário responsável pela ação (quando aplicável).
        acao (str): Tipo de ação realizada (ex: "UPDATE", "DELETE", "LOGIN", etc.).
        entidade (Optional[str]): Nome da entidade afetada (quando aplicável).
        valor_anterior (Optional[str]): Valor anterior da entidade (serializado, quando aplicável).
        valor_novo (Optional[str]): Novo valor da entidade (serializado, quando aplicável).
        detalhes (Optional[str]): Detalhes adicionais sobre a ação (ex: motivo, payload extra).
        ip (Optional[str]): Endereço IP de origem da ação.
        data_hora (datetime): Data e hora em que a ação foi realizada.
        usuario (Usuario): Relação para o usuário responsável pela ação.
    """

    __tablename__ = "auditoria"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=True)
    username = db.Column(db.String(150), nullable=True)
    acao = db.Column(db.String(100), nullable=False)  # Ex: 'UPDATE', 'DELETE', 'LOGIN', etc.
    entidade = db.Column(db.String(100), nullable=True)
    valor_anterior = db.Column(db.Text, nullable=True)
    valor_novo = db.Column(db.Text, nullable=True)
    detalhes = db.Column(db.Text, nullable=True)  # Detalhes adicionais (payload, erros, etc.)
    ip = db.Column(db.String(45), nullable=True)
    data_hora = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    usuario = db.relationship("Usuario", lazy="joined")

    def __repr__(self) -> str:
        return (
            f'<Auditoria {self.acao} - {self.entidade or "Evento"}'
            f' by {self.username or (self.usuario.nome if self.usuario else "sistema")}'
            f" at {self.data_hora}>"
        )