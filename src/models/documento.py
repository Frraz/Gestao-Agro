# src/models/documento.py

"""
Modelo para cadastro e gerenciamento de documentos associados a fazendas/áreas e/ou pessoas.

Inclui enums para tipos de documento, campos para notificações configuráveis,
relacionamentos com fazenda e pessoa, além de propriedades utilitárias para manipulação de notificações e vencimentos.
"""

import datetime
import enum
import json
from typing import Any, List, Optional, Union

from sqlalchemy import (
    Column,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from src.models.db import db

class TipoDocumento(enum.Enum):
    """Enumeração dos tipos de documentos possíveis."""
    CERTIDOES = "Certidões"
    CONTRATOS = "Contratos"
    DOCUMENTOS_AREA = "Documentos da Área"
    OUTROS = "Outros"

# REMOVIDO TipoEntidade e a coluna tipo_entidade,
# pois agora um documento pode ser associado a fazenda, pessoa, ambos ou nenhum.

class Documento(db.Model):
    """
    Modelo para cadastro de documentos associados às fazendas/áreas e/ou pessoas.

    Attributes:
        id (int): Identificador único do documento.
        nome (str): Nome do documento.
        tipo (TipoDocumento): Tipo do documento (enum).
        tipo_personalizado (Optional[str]): Detalhes adicionais do tipo.
        data_emissao (datetime.date): Data de emissão do documento.
        data_vencimento (Optional[datetime.date]): Data de vencimento do documento.
        fazenda_id (Optional[int]): ID da fazenda relacionada.
        pessoa_id (Optional[int]): ID da pessoa relacionada.
        data_criacao (datetime.date): Data de criação do registro.
        data_atualizacao (datetime.date): Data da última atualização do registro.
        fazenda (Fazenda): Relação com a fazenda.
        pessoa (Pessoa): Relação com a pessoa.
    """

    __tablename__ = "documento"

    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False, index=True)
    tipo = Column(Enum(TipoDocumento), nullable=False, index=True)
    tipo_personalizado = Column(String(100), nullable=True)
    data_emissao = Column(Date, nullable=False)
    data_vencimento = Column(Date, nullable=True, index=True)
    fazenda_id = Column(
        Integer,
        ForeignKey("fazenda.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    pessoa_id = Column(
        Integer, ForeignKey("pessoa.id", ondelete="SET NULL"), nullable=True, index=True
    )
    _emails_notificacao = Column("emails_notificacao", Text, nullable=True)
    _prazos_notificacao = Column("prazos_notificacao", Text, nullable=True)
    data_criacao = Column(Date, default=datetime.date.today, nullable=False)
    data_atualizacao = Column(Date, default=datetime.date.today, onupdate=datetime.date.today, nullable=False)

    fazenda = relationship("Fazenda", back_populates="documentos", lazy="joined")
    pessoa = relationship("Pessoa", back_populates="documentos", lazy="joined")

    __table_args__ = (
        Index("idx_documento_tipo_vencimento", "tipo", "data_vencimento"),
    )

    def __repr__(self) -> str:
        """
        Retorna representação textual do documento.
        """
        entidades = []
        if self.fazenda_id and self.fazenda:
            entidades.append(f"Fazenda: {self.fazenda.nome}")
        if self.pessoa_id and self.pessoa:
            entidades.append(f"Pessoa: {self.pessoa.nome}")
        if not entidades:
            entidades.append("Não associado")
        return f"<Documento {self.nome} - {self.tipo.value} - {' | '.join(entidades)}>"

    @property
    def emails_notificacao(self) -> List[str]:
        if not self._emails_notificacao:
            return []
        try:
            return json.loads(self._emails_notificacao)
        except json.JSONDecodeError:
            return []

    @emails_notificacao.setter
    def emails_notificacao(self, value: Union[List[str], str]) -> None:
        try:
            if isinstance(value, list):
                self._emails_notificacao = json.dumps(value)
            elif isinstance(value, str):
                emails = [email.strip() for email in value.split(",") if email.strip()]
                self._emails_notificacao = json.dumps(emails)
            else:
                self._emails_notificacao = json.dumps([])
        except Exception:
            self._emails_notificacao = json.dumps([])

    @property
    def prazos_notificacao(self) -> List[int]:
        if not self._prazos_notificacao:
            return []
        try:
            return json.loads(self._prazos_notificacao)
        except json.JSONDecodeError:
            return []

    @prazos_notificacao.setter
    def prazos_notificacao(self, value: Union[List[int], str]) -> None:
        try:
            if isinstance(value, list):
                self._prazos_notificacao = json.dumps(value)
            elif isinstance(value, str):
                try:
                    prazos = [
                        int(prazo.strip())
                        for prazo in value.split(",")
                        if prazo.strip()
                    ]
                    self._prazos_notificacao = json.dumps(prazos)
                except ValueError:
                    self._prazos_notificacao = json.dumps([30])
            else:
                self._prazos_notificacao = json.dumps([30])
        except Exception:
            self._prazos_notificacao = json.dumps([30])

    @property
    def esta_vencido(self) -> bool:
        if not self.data_vencimento:
            return False
        return datetime.date.today() > self.data_vencimento

    @property
    def proximo_vencimento(self) -> Optional[int]:
        if not self.data_vencimento:
            return None
        dias = (self.data_vencimento - datetime.date.today()).days
        return dias

    @property
    def precisa_notificar(self) -> bool:
        if not self.data_vencimento:
            return False
        dias = self.proximo_vencimento
        if dias is None:
            return False
        return dias >= 0 and dias in self.prazos_notificacao

    @property
    def entidades_relacionadas(self) -> List[Any]:
        """
        Retorna a lista de entidades relacionadas (fazenda e/ou pessoa).
        """
        entidades = []
        if self.fazenda:
            entidades.append(self.fazenda)
        if self.pessoa:
            entidades.append(self.pessoa)
        return entidades

    @property
    def nomes_entidades(self) -> str:
        """
        Retorna os nomes das entidades relacionadas.
        """
        entidades = self.entidades_relacionadas
        if not entidades:
            return "Não definido"
        return " | ".join([e.nome for e in entidades])