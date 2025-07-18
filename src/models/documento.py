# src/models/documento.py

"""
Modelo para cadastro e gerenciamento de documentos associados a fazendas/áreas e/ou pessoas.

Inclui enums para tipos de documento, campos para notificações configuráveis,
relacionamentos com fazenda e pessoa, além de propriedades utilitárias para manipulação de notificações e vencimentos.
"""

import datetime
import enum
import json
import os
from typing import Any, Dict, List, Optional, Union, Set

from sqlalchemy import (Column, Date, DateTime, Enum, ForeignKey, Index, Integer, 
                       String, Text, Boolean)
from sqlalchemy.orm import relationship

from src.models.db import db


class TipoDocumento(enum.Enum):
    """Enumeração dos tipos de documentos possíveis."""
    CERTIDOES = "Certidões"
    CONTRATOS = "Contratos"
    DOCUMENTOS_AREA = "Documentos da Área"
    LICENCAS_AMBIENTAIS = "Licenças Ambientais"
    CERTIFICACOES = "Certificações"
    OUTROS = "Outros"


class StatusProcessamento(enum.Enum):
    """Status de processamento do documento."""
    NAO_PROCESSADO = "Não Processado"
    EM_PROCESSAMENTO = "Em Processamento"
    CONCLUIDO = "Concluído"
    ERRO = "Erro"


class Documento(db.Model):  # type: ignore
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
        responsavel_id (Optional[int]): ID do usuário responsável.
        data_criacao (datetime.date): Data de criação do registro.
        data_atualizacao (datetime.date): Data da última atualização do registro.
        caminho_arquivo (Optional[str]): Caminho do arquivo no sistema.
        tamanho_arquivo (Optional[int]): Tamanho do arquivo em bytes.
        status_processamento (StatusProcessamento): Status de processamento.
        data_processamento (Optional[datetime.datetime]): Data de processamento.
        erro_processamento (Optional[str]): Mensagem de erro de processamento.
        ultima_notificacao (Optional[datetime.date]): Data da última notificação enviada.
        link_visualizacao (Optional[str]): Link para visualização do documento.
        ativo (bool): Se o documento está ativo.
    """

    __tablename__ = "documento"

    id: int = Column(Integer, primary_key=True)
    nome: str = Column(String(100), nullable=False, index=True)
    tipo: TipoDocumento = Column(Enum(TipoDocumento), nullable=False, index=True)
    tipo_personalizado: Optional[str] = Column(
        String(100), nullable=True
    )
    data_emissao: datetime.date = Column(Date, nullable=False)
    data_vencimento: Optional[datetime.date] = Column(
        Date, nullable=True, index=True
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
    responsavel_id: Optional[int] = Column(
        Integer, ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True, index=True
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
    
    # Novos campos para gerenciamento de arquivo e processamento
    caminho_arquivo: Optional[str] = Column(String(255), nullable=True)
    tamanho_arquivo: Optional[int] = Column(Integer, nullable=True)
    status_processamento: StatusProcessamento = Column(
        Enum(StatusProcessamento), 
        default=StatusProcessamento.NAO_PROCESSADO,
        nullable=False
    )
    data_processamento: Optional[datetime.datetime] = Column(DateTime, nullable=True)
    erro_processamento: Optional[str] = Column(Text, nullable=True)
    
    # Campos para notificações avançadas
    ultima_notificacao: Optional[datetime.datetime] = Column(DateTime, nullable=True)
    notificacoes_enviadas: Optional[str] = Column(Text, nullable=True)  # JSON com histórico
    link_visualizacao: Optional[str] = Column(String(255), nullable=True)
    ativo: bool = Column(Boolean, default=True, nullable=False)

    # Relacionamentos
    fazenda = relationship("Fazenda", back_populates="documentos", lazy="joined")
    pessoa = relationship("Pessoa", back_populates="documentos", lazy="joined")
    responsavel = relationship("Usuario", backref="documentos_responsavel", lazy="joined")
    historico_notificacoes = relationship(
        "HistoricoNotificacaoDocumento", 
        back_populates="documento", 
        cascade="all, delete-orphan",
        lazy="select"
    )

    __table_args__ = (
        Index("idx_documento_tipo_vencimento", "tipo", "data_vencimento"),
        Index("idx_documento_status_processamento", "status_processamento"),
        Index("idx_documento_ativo", "ativo"),
    )

    def __repr__(self) -> str:
        """
        Retorna representação textual do documento.

        Returns:
            str: String representando o documento e entidades associadas.
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
        """Lista de emails para notificação."""
        if not self._emails_notificacao:
            return []
        try:
            return json.loads(self._emails_notificacao)
        except json.JSONDecodeError:
            return []

    @emails_notificacao.setter
    def emails_notificacao(self, value: Union[List[str], str]) -> None:
        """Define a lista de emails para notificação."""
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
        """Lista de prazos para notificação em dias."""
        if not self._prazos_notificacao:
            return []
        try:
            return json.loads(self._prazos_notificacao)
        except json.JSONDecodeError:
            return []

    @prazos_notificacao.setter
    def prazos_notificacao(self, value: Union[List[int], str]) -> None:
        """Define a lista de prazos para notificação."""
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
        """Verifica se o documento está vencido."""
        if not self.data_vencimento:
            return False
        return datetime.date.today() > self.data_vencimento

    @property
    def proximo_vencimento(self) -> Optional[int]:
        """Calcula dias até o vencimento."""
        if not self.data_vencimento:
            return None
        dias = (self.data_vencimento - datetime.date.today()).days
        return dias

    @property
    def precisa_notificar(self) -> bool:
        """Verifica se o documento precisa de notificação hoje."""
        if not self.data_vencimento:
            return False
        dias = self.proximo_vencimento
        if dias is None:
            return False
        
        # Verifica se o prazo atual está na lista de prazos para notificação
        prazos = self.prazos_notificacao or [30, 15, 7, 3, 1]  # Default se não tiver configurado
        return dias >= 0 and dias in prazos

    @property
    def entidades_relacionadas(self) -> List[Any]:
        """
        Retorna a lista de entidades relacionadas (fazenda e/ou pessoa).

        Returns:
            List[Any]: Lista de instâncias das entidades relacionadas.
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

        Returns:
            str: Nomes das entidades ou 'Não definido'.
        """
        entidades = self.entidades_relacionadas
        if not entidades:
            return "Não definido"
        return " | ".join([e.nome for e in entidades])

    @property
    def dias_desde_ultima_notificacao(self) -> Optional[int]:
        """Calcula dias desde a última notificação."""
        if not self.ultima_notificacao:
            return None
        return (datetime.datetime.now() - self.ultima_notificacao).days

    @property
    def notificacoes_enviadas_lista(self) -> List[Dict[str, Any]]:
        """Retorna o histórico de notificações enviadas em formato de lista."""
        if not self.notificacoes_enviadas:
            return []
        try:
            return json.loads(self.notificacoes_enviadas)
        except json.JSONDecodeError:
            return []

    def registrar_notificacao(self, dias_restantes: int, emails: List[str]) -> None:
        """
        Registra uma notificação enviada.
        
        Args:
            dias_restantes: Dias restantes para o vencimento
            emails: Lista de emails para os quais a notificação foi enviada
        """
        self.ultima_notificacao = datetime.datetime.now()
        
        # Adicionar ao histórico de notificações enviadas
        notificacoes = self.notificacoes_enviadas_lista
        notificacoes.append({
            "data": datetime.datetime.now().isoformat(),
            "dias_restantes": dias_restantes,
            "emails": emails
        })
        
        # Limitar o histórico a últimas 10 notificações
        if len(notificacoes) > 10:
            notificacoes = notificacoes[-10:]
        
        self.notificacoes_enviadas = json.dumps(notificacoes)

    def entidade_emails(self) -> Set[str]:
        """
        Coleta emails relacionados às entidades do documento (pessoas e fazendas).
        
        Returns:
            Set de emails únicos relacionados ao documento
        """
        emails = set()
        
        # Emails da pessoa associada
        if self.pessoa and hasattr(self.pessoa, 'email') and self.pessoa.email:
            emails.add(self.pessoa.email)
            
        # Emails de pessoas relacionadas à fazenda
        if self.fazenda and hasattr(self.fazenda, 'get_emails'):
            fazenda_emails = self.fazenda.get_emails()
            emails.update(fazenda_emails)
            
        # Email do responsável
        if self.responsavel and hasattr(self.responsavel, 'email') and self.responsavel.email:
            emails.add(self.responsavel.email)
            
        return emails
        
    @property
    def extensao_arquivo(self) -> Optional[str]:
        """Retorna a extensão do arquivo."""
        if not self.caminho_arquivo:
            return None
        return os.path.splitext(self.caminho_arquivo)[1].lower()

    @property
    def tamanho_arquivo_formatado(self) -> str:
        """Retorna o tamanho do arquivo em formato legível."""
        if not self.tamanho_arquivo:
            return "N/A"
            
        # Converter para KB, MB, GB conforme apropriado
        size = self.tamanho_arquivo
        if size < 1024:
            return f"{size} bytes"
        elif size < 1024 * 1024:
            return f"{size / 1024:.2f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.2f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.2f} GB"