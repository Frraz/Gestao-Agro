# /src/models/pessoa_fazenda.py

"""
Modelo intermediário para associação entre Pessoa e Fazenda, incluindo tipo de posse e data de fim.
"""

import enum
from sqlalchemy import Column, Integer, ForeignKey, Enum, Date, Index
from sqlalchemy.orm import relationship
from src.models.db import db

class TipoPosse(enum.Enum):
    PROPRIA = "Própria"
    ARRENDADA = "Arrendada"
    COMODATO = "Comodato"
    POSSE = "Posse"
    # Adicione mais tipos conforme necessário

class PessoaFazenda(db.Model):
    """
    Modelo de vínculo entre Pessoa e Fazenda, permitindo guardar o tipo de posse e data de término do vínculo.
    """
    __tablename__ = "pessoa_fazenda"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pessoa_id = Column(Integer, ForeignKey("pessoa.id", ondelete="CASCADE"), nullable=False, index=True)
    fazenda_id = Column(Integer, ForeignKey("fazenda.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo_posse = Column(Enum(TipoPosse, name="tipo_posse_enum"), nullable=True, index=True)
    data_fim = Column(Date, nullable=True)

    pessoa = relationship("Pessoa", back_populates="pessoas_fazenda")
    fazenda = relationship("Fazenda", back_populates="pessoas_fazenda")

    __table_args__ = (
        Index("idx_pessoa_fazenda_unico", "pessoa_id", "fazenda_id", "tipo_posse", unique=True),
    )

    def __repr__(self):
        return (
            f"<PessoaFazenda id={self.id} pessoa_id={self.pessoa_id} fazenda_id={self.fazenda_id} "
            f"tipo_posse={self.tipo_posse.value if self.tipo_posse else None} data_fim={self.data_fim}>"
        )