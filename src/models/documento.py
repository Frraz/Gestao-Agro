# src/models/documento.py

"""
Modelo para cadastro e gerenciamento de documentos associados a fazendas/áreas ou pessoas.

Inclui enums para tipos de documento e entidade, campos para notificações configuráveis,
relacionamentos com fazenda e pessoa, além de propriedades utilitárias para manipulação de notificações e vencimentos.
"""

import datetime
import enum
import json
from typing import Any, List, Optional, Union

from sqlalchemy import (Column, Date, Enum, ForeignKey, Index, Integer, String,
                        Text)
from sqlalchemy.orm import relationship

from src.models.db import db


class TipoDocumento(enum.Enum):
    """Enumeração dos tipos de documentos possíveis."""

    CERTIDOES = "Certidões"
    CONTRATOS = "Contratos"
    DOCUMENTOS_AREA = "Documentos da Área"
    OUTROS = "Outros"


class TipoEntidade(enum.Enum):
    """Enumeração para o tipo de entidade associada ao documento."""

    FAZENDA = "Fazenda/Área"
    PESSOA = "Pessoa"


class Documento(db.Model):  # type: ignore
    """
    Modelo para cadastro de documentos associados às fazendas/áreas ou pessoas.

    Attributes:
        id (int): Identificador único do documento.
        nome (str): Nome do documento.
        tipo (TipoDocumento): Tipo do documento (enum).
        tipo_personalizado (Optional[str]): Detalhes adicionais do tipo.
        data_emissao (datetime.date): Data de emissão do documento.
        data_vencimento (Optional[datetime.date]): Data de vencimento do documento.
        tipo_entidade (TipoEntidade): Tipo da entidade relacionada.
        fazenda_id (Optional[int]): ID da fazenda relacionada.
        pessoa_id (Optional[int]): ID da pessoa relacionada.
        data_criacao (datetime.date): Data de criação do registro.
        data_atualizacao (datetime.date): Data da última atualização do registro.
        fazenda (Fazenda): Relação com a fazenda.
        pessoa (Pessoa): Relação com a pessoa.
    """

    __tablename__ = "documento"

    id: int = Column(Integer, primary_key=True)
    nome: str = Column(String(100), nullable=False, index=True)
    tipo: TipoDocumento = Column(Enum(TipoDocumento), nullable=False, index=True)
    tipo_personalizado: Optional[str] = Column(
        String(100), nullable=True
    )  # Para detalhes adicionais do tipo
    data_emissao: datetime.date = Column(Date, nullable=False)
    data_vencimento: Optional[datetime.date] = Column(
        Date, nullable=True, index=True
    )  # Pode não ter vencimento
    tipo_entidade: TipoEntidade = Column(
        Enum(TipoEntidade), nullable=False, default=TipoEntidade.FAZENDA, index=True
    )
    fazenda_id: Optional[int] = Column(
        Integer,
        ForeignKey("fazenda.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    pessoa_id: Optional[int] = Column(
        Integer, ForeignKey("pessoa.id", ondelete="SET NULL"), nullable=True, index=True
    )
    _emails_notificacao: Optional[str] = Column(
        "emails_notificacao", Text, nullable=True
    )
    _prazos_notificacao: Optional[str] = Column(
        "prazos_notificacao", Text, nullable=True
    )
    data_criacao: datetime.date = Column(
        Date, default=datetime.date.today, nullable=False
    )
    data_atualizacao: datetime.date = Column(
        Date, default=datetime.date.today, onupdate=datetime.date.today, nullable=False
    )

    fazenda = relationship("Fazenda", back_populates="documentos", lazy="joined")
    pessoa = relationship("Pessoa", back_populates="documentos", lazy="joined")

    __table_args__ = (
        Index("idx_documento_tipo_vencimento", "tipo", "data_vencimento"),
        Index("idx_documento_entidade_tipo", "tipo_entidade", "tipo"),
    )

    def __repr__(self) -> str:
        """
        Retorna representação textual do documento.

        Returns:
            str: String representando o documento e entidade associada.
        """
        entidade = (
            f"Fazenda: {self.fazenda.nome}"
            if self.fazenda_id
            else f"Pessoa: {self.pessoa.nome}" if self.pessoa_id else "Não associado"
        )
        return f"<Documento {self.nome} - {self.tipo.value} - {entidade}>"

    @property
    def emails_notificacao(self) -> List[str]:
        """
        Retorna a lista de emails para notificação.

        Returns:
            List[str]: Lista de emails.
        """
        if not self._emails_notificacao:
            return []
        try:
            return json.loads(self._emails_notificacao)
        except json.JSONDecodeError:
            return []

    @emails_notificacao.setter
    def emails_notificacao(self, value: Union[List[str], str]) -> None:
        """
        Define a lista de emails para notificação.

        Args:
            value (Union[List[str], str]): Lista de emails ou string separada por vírgulas.
        """
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
        """
        Retorna a lista de prazos de notificação em dias.

        Returns:
            List[int]: Lista de prazos (dias).
        """
        if not self._prazos_notificacao:
            return []
        try:
            return json.loads(self._prazos_notificacao)
        except json.JSONDecodeError:
            return []

    @prazos_notificacao.setter
    def prazos_notificacao(self, value: Union[List[int], str]) -> None:
        """
        Define a lista de prazos de notificação.

        Args:
            value (Union[List[int], str]): Lista de inteiros ou string separada por vírgulas.
        """
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
        """
        Verifica se o documento está vencido.

        Returns:
            bool: True se vencido, False caso contrário.
        """
        if not self.data_vencimento:
            return False
        return datetime.date.today() > self.data_vencimento

    @property
    def proximo_vencimento(self) -> Optional[int]:
        """
        Calcula quantos dias faltam para o vencimento.

        Returns:
            Optional[int]: Número de dias restantes ou None se não aplicável.
        """
        if not self.data_vencimento:
            return None
        dias = (self.data_vencimento - datetime.date.today()).days
        return dias

    @property
    def precisa_notificar(self) -> bool:
        """
        Verifica se é necessário notificar sobre o vencimento.

        Returns:
            bool: True se deve notificar, False caso contrário.
        """
        if not self.data_vencimento:
            return False
        dias = self.proximo_vencimento
        if dias is None:
            return False
        return dias >= 0 and dias in self.prazos_notificacao

    @property
    def entidade_relacionada(self) -> Any:
        """
        Retorna a entidade relacionada (fazenda ou pessoa).

        Returns:
            Any: Instância da entidade relacionada ou None.
        """
        if self.tipo_entidade == TipoEntidade.FAZENDA:
            return self.fazenda
        else:
            return self.pessoa

    @property
    def nome_entidade(self) -> str:
        """
        Retorna o nome da entidade relacionada.

        Returns:
            str: Nome da entidade ou 'Não definido'.
        """
        entidade = self.entidade_relacionada
        return entidade.nome if entidade else "Não definido"