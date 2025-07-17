# /src/models/fazenda.py

"""
Modelo para cadastro e gerenciamento de fazendas/áreas associadas a pessoas.

Inclui campos de auditoria, relacionamentos com pessoas via PessoaFazenda, documentos,
áreas e vínculos de endividamento, além de propriedades utilitárias para cálculo de áreas e controle de documentação.
"""

import datetime
from typing import List

from sqlalchemy import Column, Float, Index, Integer, String
from sqlalchemy.orm import relationship

from src.models.db import db

class Fazenda(db.Model):
    """
    Modelo para cadastro de fazendas/áreas.
    """

    __tablename__ = "fazenda"

    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False, index=True)
    matricula = Column(String(50), unique=True, nullable=False, index=True)
    tamanho_total = Column(Float, nullable=False)  # em hectares
    area_consolidada = Column(Float, nullable=False)  # em hectares
    tamanho_disponivel = Column(Float, nullable=False)  # em hectares (calculado)
    municipio = Column(String(100), nullable=False, index=True)
    estado = Column(String(2), nullable=False, index=True)
    recibo_car = Column(String(100), nullable=True)

    data_criacao = Column(
        db.Date, default=datetime.date.today, nullable=False
    )
    data_atualizacao = Column(
        db.Date,
        default=datetime.date.today,
        onupdate=datetime.date.today,
        nullable=False,
    )

    # Relacionamento N:N via model intermediário (PessoaFazenda)
    pessoas_fazenda = relationship(
        "PessoaFazenda",
        back_populates="fazenda",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    documentos = relationship(
        "Documento",
        back_populates="fazenda",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    areas = relationship(
        "Area",
        back_populates="fazenda",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    endividamentos_vinculados = relationship(
        "EndividamentoFazenda",
        back_populates="fazenda",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    __table_args__ = (
        Index("idx_fazenda_estado_municipio", "estado", "municipio"),
    )

    def __repr__(self) -> str:
        return f"<Fazenda {self.nome} - {self.matricula}>"

    @property
    def calcular_tamanho_disponivel(self) -> float:
        """Calcula o tamanho disponível com base no total e na área consolidada."""
        return self.tamanho_total - self.area_consolidada

    def atualizar_tamanho_disponivel(self) -> float:
        self.tamanho_disponivel = self.calcular_tamanho_disponivel
        return self.tamanho_disponivel

    @property
    def total_documentos(self) -> int:
        return len(self.documentos) if self.documentos else 0

    @property
    def documentos_vencidos(self) -> List:
        return [doc for doc in self.documentos if getattr(doc, "esta_vencido", False)]

    @property
    def documentos_a_vencer(self) -> List:
        return [
            doc
            for doc in self.documentos
            if not getattr(doc, "esta_vencido", False) and getattr(doc, "precisa_notificar", False)
        ]

    @property
    def area_usada_credito(self) -> float:
        total_usado = 0.0
        for vinculo in self.endividamentos_vinculados:
            if getattr(vinculo, "tipo", None) == "objeto_credito" and getattr(vinculo, "hectares", None):
                total_usado += float(vinculo.hectares)
        return total_usado

    @property
    def area_disponivel_credito(self) -> float:
        return self.tamanho_disponivel - self.area_usada_credito

    @property
    def total_endividamentos(self) -> int:
        return len(self.endividamentos_vinculados) if self.endividamentos_vinculados else 0

    @property
    def pessoas_associadas(self):
        """Retorna a lista de vínculos pessoa-fazenda (PessoaFazenda)"""
        return self.pessoas_fazenda

    @property
    def total_pessoas(self) -> int:
        """Retorna o total de pessoas associadas à fazenda"""
        return len(self.pessoas_fazenda) if self.pessoas_fazenda else 0