# /src/models/endividamento.py

# Modelo para Endividamento

from src.models.db import db
from datetime import datetime

class Endividamento(db.Model):
    __tablename__ = 'endividamento'
    
    id = db.Column(db.Integer, primary_key=True)
    banco = db.Column(db.String(255), nullable=False)
    numero_proposta = db.Column(db.String(255), nullable=False)
    data_emissao = db.Column(db.Date, nullable=False)
    data_vencimento_final = db.Column(db.Date, nullable=False)
    taxa_juros = db.Column(db.Numeric(10, 4), nullable=False)
    tipo_taxa_juros = db.Column(db.String(10), nullable=False)  # 'ano' ou 'mes'
    prazo_carencia = db.Column(db.Integer, nullable=True)  # em meses
    valor_operacao = db.Column(db.Numeric(15, 2), nullable=True)  # valor total da operação
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    pessoas = db.relationship(
        'Pessoa',
        secondary='endividamento_pessoa',
        back_populates='endividamentos'
    )
    fazenda_vinculos = db.relationship(
        'EndividamentoFazenda',
        back_populates='endividamento',
        cascade='all, delete-orphan'
    )
    parcelas = db.relationship(
        'Parcela',
        back_populates='endividamento',
        cascade='all, delete-orphan',
        order_by='Parcela.data_vencimento'
    )
    notificacoes = db.relationship(
        'NotificacaoEndividamento',
        back_populates='endividamento',
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f'<Endividamento {self.banco} - {self.numero_proposta}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'banco': self.banco,
            'numero_proposta': self.numero_proposta,
            'data_emissao': self.data_emissao.isoformat() if self.data_emissao else None,
            'data_vencimento_final': self.data_vencimento_final.isoformat() if self.data_vencimento_final else None,
            'taxa_juros': float(self.taxa_juros) if self.taxa_juros else None,
            'tipo_taxa_juros': self.tipo_taxa_juros,
            'prazo_carencia': self.prazo_carencia,
            'valor_operacao': float(self.valor_operacao) if self.valor_operacao else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

# Tabela de associação para relacionamento many-to-many entre Endividamento e Pessoa
endividamento_pessoa = db.Table(
    'endividamento_pessoa',
    db.Column('endividamento_id', db.Integer, db.ForeignKey('endividamento.id'), primary_key=True),
    db.Column('pessoa_id', db.Integer, db.ForeignKey('pessoa.id'), primary_key=True)
)

class EndividamentoFazenda(db.Model):
    __tablename__ = 'endividamento_fazenda'
    
    id = db.Column(db.Integer, primary_key=True)
    endividamento_id = db.Column(db.Integer, db.ForeignKey('endividamento.id'), nullable=False)
    fazenda_id = db.Column(db.Integer, db.ForeignKey('fazenda.id'), nullable=True)
    hectares = db.Column(db.Numeric(10, 2), nullable=True)
    tipo = db.Column(db.String(50), nullable=False)  # 'objeto_credito' ou 'garantia'
    descricao = db.Column(db.Text, nullable=True)
    
    # Relacionamentos
    endividamento = db.relationship('Endividamento', back_populates='fazenda_vinculos')
    fazenda = db.relationship('Fazenda')
    
    def __repr__(self):
        return f'<EndividamentoFazenda {self.tipo} - {self.fazenda.nome if self.fazenda else "Descrição livre"}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'endividamento_id': self.endividamento_id,
            'fazenda_id': self.fazenda_id,
            'fazenda_nome': self.fazenda.nome if self.fazenda else None,
            'hectares': float(self.hectares) if self.hectares else None,
            'tipo': self.tipo,
            'descricao': self.descricao
        }

class Parcela(db.Model):
    __tablename__ = 'parcela'
    
    id = db.Column(db.Integer, primary_key=True)
    endividamento_id = db.Column(db.Integer, db.ForeignKey('endividamento.id'), nullable=False)
    data_vencimento = db.Column(db.Date, nullable=False)
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    pago = db.Column(db.Boolean, default=False)
    data_pagamento = db.Column(db.Date, nullable=True)
    valor_pago = db.Column(db.Numeric(10, 2), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    
    # Relacionamentos
    endividamento = db.relationship('Endividamento', back_populates='parcelas')
    
    def __repr__(self):
        return f'<Parcela {self.data_vencimento} - R$ {self.valor}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'endividamento_id': self.endividamento_id,
            'data_vencimento': self.data_vencimento.isoformat() if self.data_vencimento else None,
            'valor': float(self.valor) if self.valor else None,
            'pago': self.pago,
            'data_pagamento': self.data_pagamento.isoformat() if self.data_pagamento else None,
            'valor_pago': float(self.valor_pago) if self.valor_pago else None,
            'observacoes': self.observacoes
        }