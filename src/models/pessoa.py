# /src/models/pessoa.py

"""
Modelo para cadastro de pessoas e associação com fazendas/áreas, documentos e endividamentos.
Inclui campos de auditoria, relacionamentos e utilitários para análise e formatação de dados.
"""

import datetime
from typing import List

from sqlalchemy import Column, Index, Integer, String
from sqlalchemy.orm import relationship

from src.models.db import db

class Pessoa(db.Model):
    """
    Modelo para cadastro de pessoas que podem ser associadas a fazendas/áreas.
    """
    __tablename__ = "pessoa"
    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False, index=True)
    cpf_cnpj = Column(String(20), unique=True, nullable=False, index=True)
    email = Column(String(100), nullable=True, index=True)
    telefone = Column(String(20), nullable=True)
    endereco = Column(String(200), nullable=True)
    data_criacao = Column(db.Date, default=datetime.date.today, nullable=False)
    data_atualizacao = Column(db.Date, default=datetime.date.today, onupdate=datetime.date.today, nullable=False)

    # Relacionamento N:N via model intermediário (PessoaFazenda)
    pessoas_fazenda = relationship(
        "PessoaFazenda",
        back_populates="pessoa",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    documentos = relationship(
        "Documento",
        back_populates="pessoa",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    endividamentos = relationship(
        "Endividamento",
        secondary="endividamento_pessoa",
        back_populates="pessoas",
        lazy="selectin"
    )

    __table_args__ = (
        Index("idx_pessoa_nome_cpf", "nome", "cpf_cnpj"),
    )

    def __repr__(self) -> str:
        return f"<Pessoa {self.nome} - {self.cpf_cnpj}>"

    @property
    def total_fazendas(self) -> int:
        """Retorna o total de vínculos da pessoa com fazendas."""
        return len(self.pessoas_fazenda) if self.pessoas_fazenda else 0

    @property
    def fazendas_associadas(self):
        """Retorna a lista de vínculos pessoa-fazenda (PessoaFazenda)"""
        return self.pessoas_fazenda

    @property
    def total_documentos(self) -> int:
        """Retorna o total de documentos vinculados à pessoa."""
        return len(self.documentos) if self.documentos else 0

    @property
    def total_endividamentos(self) -> int:
        """Retorna o total de endividamentos vinculados à pessoa."""
        return len(self.endividamentos) if self.endividamentos else 0

    @property
    def documentos_vencidos(self) -> List:
        """Retorna a lista de documentos vencidos."""
        return [doc for doc in self.documentos if getattr(doc, "esta_vencido", False)]

    @property
    def documentos_a_vencer(self) -> List:
        """Retorna a lista de documentos que precisam de notificação (a vencer)."""
        return [
            doc
            for doc in self.documentos
            if not getattr(doc, "esta_vencido", False) and getattr(doc, "precisa_notificar", False)
        ]

    def formatar_cpf_cnpj(self) -> str:
        """Formata o CPF ou CNPJ para exibição."""
        cpf_cnpj = (self.cpf_cnpj or "").replace(".", "").replace("-", "").replace("/", "")
        if len(cpf_cnpj) == 11:
            return f"{cpf_cnpj[:3]}.{cpf_cnpj[3:6]}.{cpf_cnpj[6:9]}-{cpf_cnpj[9:]}"
        elif len(cpf_cnpj) == 14:
            return f"{cpf_cnpj[:2]}.{cpf_cnpj[2:5]}.{cpf_cnpj[5:8]}/{cpf_cnpj[8:12]}-{cpf_cnpj[12:]}"
        return self.cpf_cnpj or ""