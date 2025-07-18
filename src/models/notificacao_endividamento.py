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
        data_envio_realizado (datetime): Data real do envio
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
    data_envio_realizado: Optional[datetime] = db.Column(db.DateTime, nullable=True)  # Quando foi enviada de fato
    
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
            "data_envio_realizado": self.data_envio_realizado.isoformat() if self.data_envio_realizado else None,
            "emails": self.emails_lista,
            "ativo": self.ativo,
            "tentativas": self.tentativas,
            "erro_mensagem": self.erro_mensagem,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "atraso": self.atraso_em_horas if self.esta_atrasada else 0
        }
    
    @property
    def emails_lista(self) -> List[str]:
        """
        Converte a string JSON de emails para uma lista Python.
        
        Returns:
            Lista de emails
        """
        if not self.emails:
            return []
        try:
            return json.loads(self.emails)
        except json.JSONDecodeError:
            return []
    
    @property
    def esta_atrasada(self) -> bool:
        """
        Verifica se a notificação está atrasada.
        
        Returns:
            True se a notificação está atrasada
        """
        return not self.enviado and self.data_envio <= datetime.utcnow()
    
    @property
    def pode_reenviar(self) -> bool:
        """
        Verifica se pode tentar reenviar (máximo 3 tentativas).
        
        Returns:
            True se pode tentar reenviar
        """
        return not self.enviado and self.tentativas < 3 and self.ativo
    
    @property
    def atraso_em_horas(self) -> float:
        """
        Calcula o atraso em horas, se a notificação estiver atrasada.
        
        Returns:
            Número de horas de atraso ou 0 se não estiver atrasada
        """
        if not self.esta_atrasada:
            return 0
        
        delta = datetime.utcnow() - self.data_envio
        return delta.total_seconds() / 3600  # Converter para horas
    
    @property
    def eh_configuracao(self) -> bool:
        """
        Verifica se esta notificação é uma configuração.
        
        Returns:
            True se for uma configuração
        """
        return self.tipo_notificacao == 'config'
    
    @classmethod
    def obter_proximas(cls, limite: int = 100) -> List["NotificacaoEndividamento"]:
        """
        Obtém as próximas notificações a serem enviadas.
        
        Args:
            limite: Número máximo de notificações a retornar
            
        Returns:
            Lista de notificações pendentes
        """
        return cls.query.filter(
            cls.ativo == True,
            cls.enviado == False,
            cls.data_envio <= datetime.utcnow(),
            cls.tentativas < 3,
            cls.tipo_notificacao != 'config'
        ).order_by(
            cls.data_envio
        ).limit(limite).all()
    
    @classmethod
    def tem_configuracao_ativa(cls, endividamento_id: int) -> bool:
        """
        Verifica se um endividamento tem configuração de notificação ativa.
        
        Args:
            endividamento_id: ID do endividamento
            
        Returns:
            True se tiver configuração ativa
        """
        return db.session.query(func.count(cls.id)).filter(
            cls.endividamento_id == endividamento_id,
            cls.tipo_notificacao == 'config',
            cls.ativo == True
        ).scalar() > 0
    
    def marcar_como_enviado(self) -> None:
        """Marca a notificação como enviada com sucesso."""
        self.enviado = True
        self.data_envio_realizado = datetime.utcnow()
        self.erro_mensagem = None
        
    def registrar_erro(self, mensagem: str) -> None:
        """
        Registra um erro na tentativa de envio.
        
        Args:
            mensagem: Mensagem de erro
        """
        self.tentativas += 1
        self.erro_mensagem = mensagem
        self.updated_at = datetime.utcnow()


class HistoricoNotificacao(db.Model):  # type: ignore
    """
    Modelo para registro histórico de notificações de endividamento.
    
    Attributes:
        id (int): Identificador único do registro
        endividamento_id (int): ID do endividamento relacionado
        notificacao_id (int): ID da notificação que gerou o registro (opcional)
        tipo_notificacao (str): Tipo da notificação ('30_dias', '15_dias', etc.)
        data_envio (datetime): Data de envio da notificação
        emails_enviados (str): Lista de emails em formato JSON
        sucesso (bool): Se o envio foi bem-sucedido
        erro_mensagem (str): Mensagem de erro, se houver
    """
    __tablename__ = "historico_notificacao"
    
    id: int = db.Column(db.Integer, primary_key=True)
    endividamento_id: int = db.Column(
        db.Integer,
        db.ForeignKey("endividamento.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    notificacao_id: Optional[int] = db.Column(
        db.Integer,
        db.ForeignKey("notificacao_endividamento.id", ondelete="SET NULL"),
        nullable=True
    )
    tipo_notificacao: str = db.Column(db.String(20), nullable=False)
    data_envio: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    emails_enviados: str = db.Column(db.Text, nullable=False)
    sucesso: bool = db.Column(db.Boolean, default=True)
    erro_mensagem: Optional[str] = db.Column(db.Text, nullable=True)
    
    # Relacionamentos
    endividamento = db.relationship(
        "Endividamento",
        backref=db.backref("historico_notificacoes", cascade="all, delete-orphan"),
        lazy="joined"
    )
    
    # Índices
    __table_args__ = (
        Index('idx_historico_notif_data', 'data_envio'),
        Index('idx_historico_notif_tipo', 'tipo_notificacao'),
        Index('idx_historico_notif_sucesso', 'sucesso'),
    )
    
    def __repr__(self) -> str:
        """Representação em string do registro histórico."""
        return f"<HistoricoNotificacao {self.id} - Endividamento: {self.endividamento_id} - {self.tipo_notificacao}>"
    
    @property
    def emails_lista(self) -> List[str]:
        """
        Converte a string JSON de emails para uma lista Python.
        
        Returns:
            Lista de emails
        """
        if not self.emails_enviados:
            return []
        try:
            return json.loads(self.emails_enviados)
        except json.JSONDecodeError:
            # Tenta como lista separada por vírgula
            try:
                return [e.strip() for e in self.emails_enviados.split(",") if e.strip()]
            except:
                return []
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte o objeto para um dicionário.
        
        Returns:
            Dicionário com dados do registro histórico
        """
        return {
            "id": self.id,
            "endividamento_id": self.endividamento_id,
            "notificacao_id": self.notificacao_id,
            "tipo_notificacao": self.tipo_notificacao,
            "data_envio": self.data_envio.isoformat() if self.data_envio else None,
            "emails": self.emails_lista,
            "sucesso": self.sucesso,
            "erro_mensagem": self.erro_mensagem
        }
    
    @classmethod
    def obter_por_endividamento(cls, endividamento_id: int, limite: int = 20) -> List["HistoricoNotificacao"]:
        """
        Obtém o histórico de notificações de um endividamento.
        
        Args:
            endividamento_id: ID do endividamento
            limite: Número máximo de registros a retornar
            
        Returns:
            Lista com histórico de notificações
        """
        return cls.query.filter_by(endividamento_id=endividamento_id)\
            .order_by(cls.data_envio.desc())\
            .limit(limite)\
            .all()
    
    @classmethod
    def criar_registro(
        cls, 
        endividamento_id: int, 
        tipo_notificacao: str,
        emails: Union[List[str], str],
        notificacao_id: Optional[int] = None,
        sucesso: bool = True,
        erro_mensagem: Optional[str] = None
    ) -> "HistoricoNotificacao":
        """
        Cria um novo registro de histórico de notificação.
        
        Args:
            endividamento_id: ID do endividamento
            tipo_notificacao: Tipo da notificação
            emails: Lista de emails ou string JSON de emails
            notificacao_id: ID da notificação que gerou o registro (opcional)
            sucesso: Se o envio foi bem-sucedido
            erro_mensagem: Mensagem de erro, se houver
            
        Returns:
            Nova instância de HistoricoNotificacao
        """
        # Converter emails para formato string JSON
        if isinstance(emails, list):
            emails_json = json.dumps(emails)
        else:
            emails_json = emails
            
        historico = cls(
            endividamento_id=endividamento_id,
            notificacao_id=notificacao_id,
            tipo_notificacao=tipo_notificacao,
            emails_enviados=emails_json,
            sucesso=sucesso,
            erro_mensagem=erro_mensagem
        )
        
        db.session.add(historico)
        return historico