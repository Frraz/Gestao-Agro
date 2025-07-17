# /src/models/pessoa_fazenda.py

"""
Modelo intermediário para a relação N:N entre Pessoa e Fazenda com atributos adicionais.

Este modelo substitui a tabela simples pessoa_fazenda por uma classe completa
que permite armazenar informações específicas sobre o tipo de vínculo/posse
entre pessoas e fazendas.
"""

import datetime
import enum
from typing import Optional

from sqlalchemy import Column, Enum, ForeignKey, Integer
from sqlalchemy.orm import relationship

from src.models.db import db


class TipoPosse(enum.Enum):
    """Enumeração dos tipos de posse/vínculo entre pessoa e fazenda."""
    PROPRIA = "PROPRIA"
    ARRENDADA = "ARRENDADA"
    COMODATO = "COMODATO"
    POSSE = "POSSE"


class PessoaFazenda(db.Model):  # type: ignore
    """
    Modelo intermediário para relacionamento N:N entre Pessoa e Fazenda.
    
    Permite múltiplas associações entre a mesma pessoa e fazenda com diferentes
    tipos de posse, conforme implementado no PR #3.
    
    Attributes:
        id (int): Identificador único da associação.
        pessoa_id (int): ID da pessoa associada.
        fazenda_id (int): ID da fazenda associada.
        tipo_posse (TipoPosse): Tipo de vínculo/posse.
        pessoa (Pessoa): Referência à pessoa.
        fazenda (Fazenda): Referência à fazenda.
    """
    
    __tablename__ = "pessoa_fazenda"
    
    id = Column(Integer, primary_key=True)
    pessoa_id = Column(Integer, ForeignKey("pessoa.id", ondelete="CASCADE"), nullable=False)
    fazenda_id = Column(Integer, ForeignKey("fazenda.id", ondelete="CASCADE"), nullable=False)
    tipo_posse = Column(Enum(TipoPosse), nullable=False)
    
    # Relacionamentos
    pessoa = relationship("Pessoa", back_populates="pessoas_fazenda")
    fazenda = relationship("Fazenda", back_populates="pessoas_fazenda")
    
    def __repr__(self) -> str:
        return f"<PessoaFazenda {self.pessoa_id}-{self.fazenda_id} ({self.tipo_posse.value})>"
    
    @property
    def tipo_posse_descricao(self) -> str:
        """Retorna descrição amigável do tipo de posse."""
        mapping = {
            TipoPosse.PROPRIA: "Própria",
            TipoPosse.ARRENDADA: "Arrendada",
            TipoPosse.COMODATO: "Comodato",
            TipoPosse.POSSE: "Posse"
        }
        return mapping.get(self.tipo_posse, self.tipo_posse.value)

