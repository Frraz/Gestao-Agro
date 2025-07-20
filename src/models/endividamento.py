# src/models/endividamento.py

"""
Modelos relacionados ao endividamento, incluindo endividamento principal, vínculo com fazenda, vínculo com área e parcelas.

Inclui:
- Endividamento: Operação financeira atrelada a pessoas, fazendas e áreas, com parcelas e notificações.
- EndividamentoFazenda: Associação entre endividamento e fazenda (opcional, caso use toda a fazenda).
- Parcela: Detalhes de cada parcela do endividamento.
"""

from datetime import datetime, date
from typing import Dict, Any, List, Optional

from sqlalchemy.ext.hybrid import hybrid_property

from src.models.db import db
# Importar a classe EndividamentoArea em vez de redefini-la
from src.models.endividamento_area import EndividamentoArea


class Endividamento(db.Model):
    """
    Modelo de endividamento financeiro.
    
    Representa uma operação de crédito/endividamento com banco, parcelas e notificações.
    """
    __tablename__ = "endividamento"

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

    pessoas = db.relationship(
        "Pessoa", secondary="endividamento_pessoa", back_populates="endividamentos"
    )
    fazenda_vinculos = db.relationship(
        "EndividamentoFazenda",
        back_populates="endividamento",
        cascade="all, delete-orphan",
    )
    area_vinculos = db.relationship(
        "EndividamentoArea",
        back_populates="endividamento",
        cascade="all, delete-orphan",
    )
    parcelas = db.relationship(
        "Parcela",
        back_populates="endividamento",
        cascade="all, delete-orphan",
        order_by="Parcela.data_vencimento",
    )
    notificacoes = db.relationship(
        "NotificacaoEndividamento",
        back_populates="endividamento",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Endividamento {self.banco} - {self.numero_proposta}>"

    def to_dict(self) -> Dict[str, Any]:
        """
        Converte o endividamento para um dicionário.
        
        Returns:
            Dicionário com os dados do endividamento
        """
        return {
            "id": self.id,
            "banco": self.banco,
            "numero_proposta": self.numero_proposta,
            "data_emissao": (
                self.data_emissao.isoformat() if self.data_emissao else None
            ),
            "data_vencimento_final": (
                self.data_vencimento_final.isoformat()
                if self.data_vencimento_final
                else None
            ),
            "taxa_juros": float(self.taxa_juros) if self.taxa_juros else None,
            "tipo_taxa_juros": self.tipo_taxa_juros,
            "prazo_carencia": self.prazo_carencia,
            "valor_operacao": (
                float(self.valor_operacao) if self.valor_operacao else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @hybrid_property
    def esta_vencido(self) -> bool:
        """
        Verifica se o endividamento está vencido.
        
        Returns:
            True se a data de vencimento é anterior à data atual
        """
        return self.data_vencimento_final < date.today() if self.data_vencimento_final else False

    @hybrid_property
    def dias_ate_vencimento(self) -> Optional[int]:
        """
        Calcula quantos dias faltam para o vencimento.
        
        Returns:
            Número de dias até o vencimento ou None se não houver data de vencimento
        """
        if not self.data_vencimento_final:
            return None
        
        delta = self.data_vencimento_final - date.today()
        return delta.days
    
    @hybrid_property
    def parcelas_pendentes(self) -> List["Parcela"]:
        """
        Obtém as parcelas pendentes (não pagas).
        
        Returns:
            Lista de parcelas não pagas
        """
        return [p for p in self.parcelas if not p.pago]
    
    @hybrid_property
    def parcelas_pagas(self) -> List["Parcela"]:
        """
        Obtém as parcelas já pagas.
        
        Returns:
            Lista de parcelas pagas
        """
        return [p for p in self.parcelas if p.pago]

    @hybrid_property
    def proxima_parcela(self) -> Optional["Parcela"]:
        """
        Obtém a próxima parcela a vencer.
        
        Returns:
            Próxima parcela a vencer ou None se não houver
        """
        hoje = date.today()
        parcelas_futuras = [p for p in self.parcelas if not p.pago and p.data_vencimento >= hoje]
        return min(parcelas_futuras, key=lambda p: p.data_vencimento) if parcelas_futuras else None
    
    @hybrid_property
    def valor_pendente(self) -> float:
        """
        Calcula o valor total ainda pendente de pagamento.
        
        Returns:
            Soma dos valores das parcelas não pagas
        """
        return sum(float(p.valor) for p in self.parcelas_pendentes)

    @hybrid_property
    def valor_pago(self) -> float:
        """
        Calcula o valor total já pago.
        
        Returns:
            Soma dos valores das parcelas pagas
        """
        return sum(float(p.valor_pago or p.valor) for p in self.parcelas_pagas)

    def obter_config_notificacao(self) -> Dict[str, Any]:
        """
        Obtém a configuração de notificação atual.
        
        Returns:
            Dicionário com a configuração de notificação
        """
        config = next((n for n in self.notificacoes if n.tipo_notificacao == 'config' and n.ativo), None)
        
        if not config:
            return {
                "ativo": False,
                "emails": [],
                "ultima_atualizacao": None
            }
        
        emails = []
        try:
            if config.emails:
                if isinstance(config.emails, str):
                    import json
                    emails = json.loads(config.emails)
                else:
                    emails = config.emails
        except Exception:
            emails = []
            
        return {
            "ativo": config.ativo,
            "emails": emails,
            "ultima_atualizacao": config.updated_at
        }
        
    def tem_notificacoes_ativas(self) -> bool:
        """
        Verifica se o endividamento possui notificações ativas.
        
        Returns:
            True se existem notificações ativas configuradas
        """
        return any(n for n in self.notificacoes if n.ativo and n.tipo_notificacao == 'config')


# Tabela de associação para relacionamento many-to-many entre Endividamento e Pessoa
endividamento_pessoa = db.Table(
    "endividamento_pessoa",
    db.Column(
        "endividamento_id",
        db.Integer,
        db.ForeignKey("endividamento.id"),
        primary_key=True,
    ),
    db.Column("pessoa_id", db.Integer, db.ForeignKey("pessoa.id"), primary_key=True),
)


class EndividamentoFazenda(db.Model):
    """
    Modelo de vínculo entre endividamento e fazenda.
    
    Representa uma associação entre um endividamento e uma fazenda,
    podendo ser do tipo 'objeto_credito' (área financiada) ou 'garantia'.
    """
    __tablename__ = "endividamento_fazenda"

    id = db.Column(db.Integer, primary_key=True)
    endividamento_id = db.Column(
        db.Integer, db.ForeignKey("endividamento.id"), nullable=False
    )
    fazenda_id = db.Column(
        db.Integer, db.ForeignKey("fazenda.id"), nullable=True
    )
    hectares = db.Column(db.Numeric(10, 2), nullable=True)
    tipo = db.Column(
        db.String(50), nullable=False
    )  # 'objeto_credito' ou 'garantia'
    descricao = db.Column(db.Text, nullable=True)

    endividamento = db.relationship("Endividamento", back_populates="fazenda_vinculos")
    fazenda = db.relationship("Fazenda")

    def __repr__(self) -> str:
        return f'<EndividamentoFazenda {self.tipo} - {self.fazenda.nome if self.fazenda else "Descrição livre"}>'

    def to_dict(self) -> Dict[str, Any]:
        """
        Converte o vínculo de fazenda para um dicionário.
        
        Returns:
            Dicionário com os dados do vínculo
        """
        return {
            "id": self.id,
            "endividamento_id": self.endividamento_id,
            "fazenda_id": self.fazenda_id,
            "fazenda_nome": self.fazenda.nome if self.fazenda else None,
            "hectares": float(self.hectares) if self.hectares else None,
            "tipo": self.tipo,
            "descricao": self.descricao,
        }


class Parcela(db.Model):
    """
    Modelo de parcela de endividamento.
    
    Representa uma parcela a ser paga de um endividamento,
    contendo data de vencimento, valor, status de pagamento e observações.
    """
    __tablename__ = "parcela"

    id = db.Column(db.Integer, primary_key=True)
    endividamento_id = db.Column(
        db.Integer, db.ForeignKey("endividamento.id"), nullable=False
    )
    data_vencimento = db.Column(db.Date, nullable=False)
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    pago = db.Column(db.Boolean, default=False)
    data_pagamento = db.Column(db.Date, nullable=True)
    valor_pago = db.Column(db.Numeric(10, 2), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)

    endividamento = db.relationship("Endividamento", back_populates="parcelas")

    def __repr__(self) -> str:
        return f"<Parcela {self.data_vencimento} - R$ {self.valor}>"

    def to_dict(self) -> Dict[str, Any]:
        """
        Converte a parcela para um dicionário.
        
        Returns:
            Dicionário com os dados da parcela
        """
        return {
            "id": self.id,
            "endividamento_id": self.endividamento_id,
            "data_vencimento": (
                self.data_vencimento.isoformat() if self.data_vencimento else None
            ),
            "valor": float(self.valor) if self.valor else None,
            "pago": self.pago,
            "data_pagamento": (
                self.data_pagamento.isoformat() if self.data_pagamento else None
            ),
            "valor_pago": float(self.valor_pago) if self.valor_pago else None,
            "observacoes": self.observacoes,
        }