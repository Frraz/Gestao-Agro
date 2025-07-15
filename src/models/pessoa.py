# /src/models/pessoa.py

"""
Modelo para cadastro de pessoas e associação com fazendas/áreas, documentos e endividamentos.

Inclui tabela de associação pessoa_fazenda, campos de auditoria, relacionamentos e utilitários para análise e formatação de dados.
"""

import datetime
from typing import List, Optional

from sqlalchemy import Column, ForeignKey, Index, Integer, String, Table
from sqlalchemy.orm import relationship

from src.models.db import db

# Tabela de associação entre Pessoa e Fazenda (relação muitos-para-muitos)
pessoa_fazenda = Table(
    "pessoa_fazenda",
    db.Model.metadata,
    Column(
        "pessoa_id",
        Integer,
        ForeignKey("pessoa.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "fazenda_id",
        Integer,
        ForeignKey("fazenda.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Index("idx_pessoa_fazenda", "pessoa_id", "fazenda_id"),
)


class Pessoa(db.Model):  # type: ignore
    """
    Modelo para cadastro de pessoas que podem ser associadas a fazendas/áreas.

    Attributes:
        id (int): Identificador.
        nome (str): Nome da pessoa.
        cpf_cnpj (str): CPF ou CNPJ.
        email (Optional[str]): Email da pessoa.
        telefone (Optional[str]): Telefone da pessoa.
        endereco (Optional[str]): Endereço.
        data_criacao (datetime.date): Data de criação.
        data_atualizacao (datetime.date): Data de atualização.
        fazendas (List[Fazenda]): Fazendas associadas.
        documentos (List[Documento]): Documentos associados.
        endividamentos (List[Endividamento]): Endividamentos associados.
    """

    __tablename__ = "pessoa"

    id: int = Column(Integer, primary_key=True)
    nome: str = Column(String(100), nullable=False, index=True)
    cpf_cnpj: str = Column(String(20), unique=True, nullable=False, index=True)
    email: Optional[str] = Column(String(100), nullable=True, index=True)
    telefone: Optional[str] = Column(String(20), nullable=True)
    endereco: Optional[str] = Column(String(200), nullable=True)

    data_criacao: datetime.date = Column(
        db.Date, default=datetime.date.today, nullable=False
    )
    data_atualizacao: datetime.date = Column(
        db.Date,
        default=datetime.date.today,
        onupdate=datetime.date.today,
        nullable=False,
    )

    fazendas = relationship(
        "Fazenda", secondary=pessoa_fazenda, back_populates="pessoas", lazy="selectin"
    )
    documentos = relationship(
        "Documento",
        back_populates="pessoa",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    endividamentos = relationship(
        "Endividamento", secondary="endividamento_pessoa", back_populates="pessoas"
    )

    __table_args__ = (Index("idx_pessoa_nome_cpf", "nome", "cpf_cnpj"),)

    def __repr__(self) -> str:
        return f"<Pessoa {self.nome} - {self.cpf_cnpj}>"

    @property
    def total_fazendas(self) -> int:
        """Retorna o número total de fazendas associadas à pessoa."""
        return len(self.fazendas) if self.fazendas else 0

    @property
    def total_documentos(self) -> int:
        """Retorna o número total de documentos associados à pessoa."""
        return len(self.documentos) if self.documentos else 0

    @property
    def total_endividamentos(self) -> int:
        """Retorna o número total de endividamentos associados à pessoa."""
        return len(self.endividamentos) if self.endividamentos else 0

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

    def formatar_cpf_cnpj(self) -> str:
        """Formata o CPF/CNPJ para exibição."""
        cpf_cnpj = self.cpf_cnpj.replace(".", "").replace("-", "").replace("/", "")
        if len(cpf_cnpj) == 11:  # CPF
            return f"{cpf_cnpj[:3]}.{cpf_cnpj[3:6]}.{cpf_cnpj[6:9]}-{cpf_cnpj[9:]}"
        elif len(cpf_cnpj) == 14:  # CNPJ
            return f"{cpf_cnpj[:2]}.{cpf_cnpj[2:5]}.{cpf_cnpj[5:8]}/{cpf_cnpj[8:12]}-{cpf_cnpj[12:]}"
        return self.cpf_cnpj  # Retorna como está se não for CPF nem CNPJ