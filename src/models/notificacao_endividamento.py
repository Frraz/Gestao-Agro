# /src/models/notificacao_endividamento.py

"""
Modelos para notificações e histórico de notificações de endividamento.
Gerencia o agendamento, envio e registro histórico de notificações de vencimentos.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Boolean, Index, func
from sqlalchemy.orm import relationship

from src.models.db import db


class NotificacaoEndividamento(db.Model):  # type: ignore
    """
    Modelo para notificações de endividamento agendadas.
    
    Attributes:
        id (int): Identificador único da notificação
        endividamento_id (int): ID do endividamento relacionado
        tipo_notificacao (str): Tipo da notificação ('30_dias', '15_dias', 'config', etc.)
        data_envio (datetime): Data agendada para envio
        enviado (bool): Se a notificação já foi enviada
        emails (str): Lista de emails em formato JSON
        ativo (bool): Se a notificação está ativa
        tentativas (int): Número de tentativas de envio
        erro_mensagem (str): Mensagem de erro da última tentativa
        created_at (datetime): Data de criação do registro
        updated_at (datetime): Data de atualização do registro
    """
    __tablename__ = "notificacao_endividamento"

    id: int = db.Column(db.Integer, primary_key=True)
    endividamento_id: int = db.Column(
        db.Integer, 
        db.ForeignKey("endividamento.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    
    # Campos essenciais para agendamento
    tipo_notificacao: str = db.Column(db.String(20), nullable=False, index=True)  # '30_dias', '15_dias', etc.
    data_envio: datetime = db.Column(db.DateTime, nullable=False, index=True)  # Quando deve ser enviada
    enviado: bool = db.Column(db.Boolean, default=False, index=True)  # Se já foi enviada
    # Removida a coluna data_envio_realizado que não existe no banco de dados
    
    emails: str = db.Column(db.Text, nullable=False)  # JSON string com lista de emails
    ativo: bool = db.Column(db.Boolean, default=True, index=True)
    tentativas: int = db.Column(db.Integer, default=0)  # Número de tentativas de envio
    erro_mensagem: Optional[str] = db.Column(db.Text, nullable=True)  # Último erro, se houver
    
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at: datetime = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relacionamentos
    endividamento = db.relationship(
        "Endividamento", 
        back_populates="notificacoes",
        lazy="joined"
    )
    
    # Índices adicionais
    __table_args__ = (
        Index('idx_notif_endiv_ativa_pendente', 'ativo', 'enviado', 'data_envio'),
        Index('idx_notif_endiv_tipo', 'tipo_notificacao'),
    )

    def __repr__(self) -> str:
        """Representação em string da notificação."""
        return f"<NotificacaoEndividamento {self.id} - {self.tipo_notificacao} - Enviado: {self.enviado}>"

    def to_dict(self) -> Dict[str, Any]:
        """
        Converte o objeto para um dicionário.
        
        Returns:
            Dicionário com dados da notificação
        """
        return {
            "id": self.id,
            "endividamento_id": self.endividamento_id,
            "tipo_notificacao": self.tipo_notificacao,
            "data_envio": self.data_envio.isoformat() if self.data_envio else None,
            "enviado": self.enviado,
            "emails": self.emails_lista if hasattr(self, 'emails_lista') else self.emails,
            "ativo": self.ativo,
            "tentativas": self.tentativas,
            "erro_mensagem": self.erro_mensagem,
        }
    
    @property
    def emails_lista(self) -> List[str]:
        """
        Converte o texto JSON de emails em uma lista Python.
        
        Returns:
            Lista de endereços de email
        """
        if not self.emails:
            return []
        try:
            return json.loads(self.emails)
        except json.JSONDecodeError:
            # Fallback: assume que é uma string simples separada por vírgulas
            return [email.strip() for email in self.emails.split(',') if email.strip()]