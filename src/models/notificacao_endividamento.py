# Modelo para Notificações de Endividamento
from src.models.db import db
from datetime import datetime

class NotificacaoEndividamento(db.Model):
    __tablename__ = 'notificacao_endividamento'
    
    id = db.Column(db.Integer, primary_key=True)
    endividamento_id = db.Column(db.Integer, db.ForeignKey('endividamento.id'), nullable=False)
    emails = db.Column(db.Text, nullable=False)  # JSON string com lista de emails
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamento explícito usando back_populates
    endividamento = db.relationship(
        'Endividamento',
        back_populates='notificacoes'
    )
    
    def __repr__(self):
        return f'<NotificacaoEndividamento {self.endividamento_id}>'
    
    def to_dict(self):
        import json
        return {
            'id': self.id,
            'endividamento_id': self.endividamento_id,
            'emails': json.loads(self.emails) if self.emails else [],
            'ativo': self.ativo,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class HistoricoNotificacao(db.Model):
    __tablename__ = 'historico_notificacao'
    
    id = db.Column(db.Integer, primary_key=True)
    endividamento_id = db.Column(db.Integer, db.ForeignKey('endividamento.id'), nullable=False)
    tipo_notificacao = db.Column(db.String(20), nullable=False)  # '6_meses', '3_meses', '30_dias', etc.
    data_envio = db.Column(db.DateTime, default=datetime.utcnow)
    emails_enviados = db.Column(db.Text, nullable=False)  # JSON string com lista de emails
    sucesso = db.Column(db.Boolean, default=True)
    erro_mensagem = db.Column(db.Text, nullable=True)
    
    # Relacionamento simples (caso queira histórico por endividamento)
    endividamento = db.relationship('Endividamento')
    
    def __repr__(self):
        return f'<HistoricoNotificacao {self.endividamento_id} - {self.tipo_notificacao}>'
    
    def to_dict(self):
        import json
        return {
            'id': self.id,
            'endividamento_id': self.endividamento_id,
            'tipo_notificacao': self.tipo_notificacao,
            'data_envio': self.data_envio.isoformat() if self.data_envio else None,
            'emails_enviados': json.loads(self.emails_enviados) if self.emails_enviados else [],
            'sucesso': self.sucesso,
            'erro_mensagem': self.erro_mensagem
        }