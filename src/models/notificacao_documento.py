# src/models/notificacao_documento.py

"""
Modelo para histórico de notificações de documentos.
"""

import datetime
import json
from typing import List, Dict, Any, Optional

from sqlalchemy import (Column, DateTime, ForeignKey, Integer, String, 
                       Text, Boolean, Index)
from sqlalchemy.orm import relationship

from src.models.db import db


class HistoricoNotificacaoDocumento(db.Model):  # type: ignore
    """
    Modelo para registro do histórico de notificações enviadas para documentos.
    
    Attributes:
        id (int): Identificador único.
        documento_id (int): ID do documento notificado.
        data_envio (datetime): Data e hora do envio da notificação.
        dias_restantes (int): Dias restantes até o vencimento no momento do envio.
        destinatarios (str): Lista de destinatários da notificação.
        tipo_notificacao (str): Tipo da notificação (vencimento, atraso, etc).
        sucesso (bool): Se o envio foi bem sucedido.
        erro_mensagem (Optional[str]): Mensagem de erro, se houver.
    """
    
    __tablename__ = "historico_notificacao_documento"
    
    id: int = Column(Integer, primary_key=True)
    documento_id: int = Column(
        Integer, 
        ForeignKey("documento.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    data_envio: datetime.datetime = Column(
        DateTime, 
        default=datetime.datetime.now,
        nullable=False
    )
    dias_restantes: int = Column(Integer, nullable=False)
    destinatarios: str = Column(Text, nullable=False)
    tipo_notificacao: str = Column(String(20), nullable=False)
    sucesso: bool = Column(Boolean, default=True, nullable=False)
    erro_mensagem: Optional[str] = Column(Text, nullable=True)
    
    # Relacionamentos
    documento = relationship(
        "Documento",
        back_populates="historico_notificacoes",
        lazy="joined"
    )
    
    __table_args__ = (
        Index("idx_historico_notificacao_documento_data", "data_envio"),
        Index("idx_historico_notificacao_documento_tipo", "tipo_notificacao"),
    )
    
    def __repr__(self) -> str:
        """Representação textual do histórico."""
        return (
            f"<HistoricoNotificacaoDocumento {self.id} - "
            f"Documento: {self.documento_id}, "
            f"Data: {self.data_envio}, "
            f"Dias: {self.dias_restantes}>"
        )
    
    @property
    def destinatarios_lista(self) -> List[str]:
        """Retorna lista de destinatários."""
        try:
            return self.destinatarios.split(',')
        except:
            return []
    
    @classmethod
    def obter_historico_documento(cls, documento_id: int, limit: int = 20) -> List["HistoricoNotificacaoDocumento"]:
        """
        Obtém o histórico de notificações de um documento.
        
        Args:
            documento_id: ID do documento
            limit: Limite de registros
            
        Returns:
            Lista com histórico de notificações
        """
        return cls.query.filter_by(documento_id=documento_id)\
            .order_by(cls.data_envio.desc())\
            .limit(limit)\
            .all()