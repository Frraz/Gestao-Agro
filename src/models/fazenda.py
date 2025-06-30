# /src/models/fazenda.py

"""
Modelo para cadastro e gerenciamento de fazendas/áreas associadas a pessoas.

Inclui enum para tipo de posse, campos de auditoria, relacionamentos com pessoas e documentos,
e propriedades utilitárias para cálculo de áreas e controle de documentação.
"""

import datetime
import enum
from typing import List, Optional

from sqlalchemy import Column, Enum, Float, Index, Integer, String
from sqlalchemy.orm import relationship

from src.models.db import db

from .pessoa import pessoa_fazenda


class TipoPosse(enum.Enum):
    """Enumeração dos tipos de posse da fazenda."""

    PROPRIA = "Própria"
    ARRENDADA = "Arrendada"
    COMODATO = "Comodato"
    POSSE = "Posse"


class Fazenda(db.Model):  # type: ignore
    """
    Modelo para cadastro de fazendas/áreas.

    Attributes:
        id (int): Identificador único da fazenda.
        nome (str): Nome da fazenda.
        matricula (str): Número da matrícula da fazenda.
        tamanho_total (float): Tamanho total da fazenda (ha).
        area_consolidada (float): Área consolidada (ha).
        tamanho_disponivel (float): Área disponível (ha).
        tipo_posse (TipoPosse): Tipo de posse.
        municipio (str): Município da fazenda.
        estado (str): UF da fazenda.
        recibo_car (Optional[str]): Número do recibo do CAR.
        data_criacao (datetime.date): Data de criação.
        data_atualizacao (datetime.date): Data de atualização.
        pessoas (List[Pessoa]): Pessoas associadas.
        documentos (List[Documento]): Documentos associados.
    """

    __tablename__ = "fazenda"

    id: int = Column(Integer, primary_key=True)
    nome: str = Column(String(100), nullable=False, index=True)
    matricula: str = Column(String(50), unique=True, nullable=False, index=True)
    tamanho_total: float = Column(Float, nullable=False)  # em hectares
    area_consolidada: float = Column(Float, nullable=False)  # em hectares
    tamanho_disponivel: float = Column(Float, nullable=False)  # em hectares (calculado)
    tipo_posse: TipoPosse = Column(Enum(TipoPosse), nullable=False, index=True)
    municipio: str = Column(String(100), nullable=False, index=True)
    estado: str = Column(String(2), nullable=False, index=True)
    recibo_car: Optional[str] = Column(String(100), nullable=True)

    data_criacao: datetime.date = Column(
        db.Date, default=datetime.date.today, nullable=False
    )
    data_atualizacao: datetime.date = Column(
        db.Date,
        default=datetime.date.today,
        onupdate=datetime.date.today,
        nullable=False,
    )

    pessoas = relationship(
        "Pessoa", secondary=pessoa_fazenda, back_populates="fazendas", lazy="selectin"
    )
    documentos = relationship(
        "Documento",
        back_populates="fazenda",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_fazenda_estado_municipio", "estado", "municipio"),
        Index("idx_fazenda_tipo_posse", "tipo_posse"),
    )

    def __repr__(self) -> str:
        return f"<Fazenda {self.nome} - {self.matricula}>"

    @property
    def calcular_tamanho_disponivel(self) -> float:
        """Calcula o tamanho disponível com base no total e na área consolidada."""
        return self.tamanho_total - self.area_consolidada

    def atualizar_tamanho_disponivel(self) -> float:
        """
        Atualiza o campo tamanho_disponivel com base nos valores atuais.

        Returns:
            float: Novo valor do campo tamanho_disponivel.
        """
        self.tamanho_disponivel = self.calcular_tamanho_disponivel
        return self.tamanho_disponivel

    @property
    def total_documentos(self) -> int:
        """Retorna o número total de documentos associados à fazenda."""
        return len(self.documentos) if self.documentos else 0

    @property
    def documentos_vencidos(self) -> List:
        """Retorna a lista de documentos vencidos."""
        return [doc for doc in self.documentos if doc.esta_vencido]

    @property
    def documentos_a_vencer(self) -> List:
        """Retorna a lista de documentos próximos do vencimento."""
        return [
            doc
            for doc in self.documentos
            if not doc.esta_vencido and doc.precisa_notificar
        ]
