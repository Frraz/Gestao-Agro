# /src/models/fazenda.py

"""
Modelo para cadastro e gerenciamento de fazendas/áreas associadas a pessoas.
Inclui relacionamentos com pessoas através do modelo intermediário PessoaFazenda,
campos de auditoria, relacionamentos com documentos, áreas e vínculos de endividamento,
além de propriedades utilitárias para cálculo de áreas e controle de documentação.
"""

import datetime
from typing import List, Optional


from sqlalchemy import Column, Float, Index, Integer, String
from sqlalchemy.orm import relationship

from src.models.db import db


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
        municipio (str): Município da fazenda.
        estado (str): UF da fazenda.
        recibo_car (Optional[str]): Número do recibo do CAR.
        data_criacao (datetime.date): Data de criação.
        data_atualizacao (datetime.date): Data de atualização.
        pessoas_fazenda (List[PessoaFazenda]): Vínculos com pessoas através do modelo intermediário.
        documentos (List[Documento]): Documentos associados.
        endividamentos_vinculados (List[EndividamentoFazenda]): Vínculos de endividamento (por fazenda).
        areas (List[Area]): Áreas pertencentes à fazenda.

    """

    __tablename__ = "fazenda"

    id: int = Column(Integer, primary_key=True)
    nome: str = Column(String(100), nullable=False, index=True)
    matricula: str = Column(String(50), unique=True, nullable=False, index=True)
    tamanho_total: float = Column(Float, nullable=False)  # em hectares
    area_consolidada: float = Column(Float, nullable=False)  # em hectares
    tamanho_disponivel: float = Column(Float, nullable=False)  # em hectares (calculado)
    municipio: str = Column(String(100), nullable=False, index=True)
    estado: str = Column(String(2), nullable=False, index=True)
    recibo_car: Optional[str] = Column(String(100), nullable=True)

    data_criacao: datetime.date = Column(

        db.Date, default=datetime.date.today, nullable=False
    )
    data_atualizacao = Column(
        db.Date,
        default=datetime.date.today,
        onupdate=datetime.date.today,
        nullable=False,
    )


    # Relacionamentos através do modelo intermediário PessoaFazenda
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

        """Retorna o número total de endividamentos vinculados (por fazenda)."""
        return len(self.endividamentos_vinculados)

    # Propriedades para compatibilidade com o novo modelo de relacionamentos
    @property
    def pessoas_associadas(self) -> List["Pessoa"]:
        """Retorna lista de pessoas associadas através dos vínculos (compatibilidade PR #4)."""
        return [vinculo.pessoa for vinculo in self.pessoas_fazenda]

    @property
    def total_pessoas(self) -> int:
        """Retorna o número total de pessoas associadas (PR #4)."""
        return len(self.pessoas_fazenda)

    def get_vinculos_por_tipo(self, tipo_posse: "TipoPosse") -> List["PessoaFazenda"]:
        """Retorna vínculos filtrados por tipo de posse."""
        from src.models.pessoa_fazenda import TipoPosse
        return [v for v in self.pessoas_fazenda if v.tipo_posse == tipo_posse]
