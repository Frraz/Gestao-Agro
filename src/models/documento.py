#src/models/documento.py
from sqlalchemy import Column, Integer, String, Date, ForeignKey, Enum, Table, Text, Index
from sqlalchemy.orm import relationship, backref
from src.models.db import db
import enum
import datetime
import json

class TipoDocumento(enum.Enum):
    CERTIDOES = "Certidões"
    CONTRATOS = "Contratos"
    DOCUMENTOS_AREA = "Documentos da Área"
    OUTROS = "Outros"

class TipoEntidade(enum.Enum):
    FAZENDA = "Fazenda/Área"
    PESSOA = "Pessoa"

class Documento(db.Model):
    """
    Modelo para cadastro de documentos associados às fazendas/áreas ou pessoas.
    """
    __tablename__ = 'documento'
    
    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False, index=True)
    tipo = Column(Enum(TipoDocumento), nullable=False, index=True)
    tipo_personalizado = Column(String(100), nullable=True)  # Para detalhes adicionais do tipo
    data_emissao = Column(Date, nullable=False)
    data_vencimento = Column(Date, nullable=True, index=True)  # Pode não ter vencimento
    
    # Tipo de entidade relacionada (Fazenda ou Pessoa)
    tipo_entidade = Column(Enum(TipoEntidade), nullable=False, default=TipoEntidade.FAZENDA, index=True)
    
    # Chaves estrangeiras (apenas uma será preenchida, dependendo do tipo_entidade)
    fazenda_id = Column(Integer, ForeignKey('fazenda.id', ondelete='SET NULL'), nullable=True, index=True)
    pessoa_id = Column(Integer, ForeignKey('pessoa.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Emails para notificação (armazenados como JSON)
    _emails_notificacao = Column("emails_notificacao", Text, nullable=True)
    
    # Prazos de notificação armazenados como JSON
    _prazos_notificacao = Column("prazos_notificacao", Text, nullable=True)
    
    # Data de criação e atualização para auditoria
    data_criacao = Column(Date, default=datetime.date.today, nullable=False)
    data_atualizacao = Column(Date, default=datetime.date.today, onupdate=datetime.date.today, nullable=False)
    
    # Relacionamentos com lazy loading otimizado
    fazenda = relationship('Fazenda', back_populates='documentos', lazy='joined')
    pessoa = relationship('Pessoa', back_populates='documentos', lazy='joined')
    
    # Índices compostos para consultas frequentes
    __table_args__ = (
        Index('idx_documento_tipo_vencimento', 'tipo', 'data_vencimento'),
        Index('idx_documento_entidade_tipo', 'tipo_entidade', 'tipo'),
    )
    
    def __repr__(self):
        entidade = f"Fazenda: {self.fazenda.nome}" if self.fazenda_id else f"Pessoa: {self.pessoa.nome}" if self.pessoa_id else "Não associado"
        return f'<Documento {self.nome} - {self.tipo.value} - {entidade}>'
    
    @property
    def emails_notificacao(self):
        """Retorna a lista de emails para notificação."""
        if not self._emails_notificacao:
            return []
        try:
            return json.loads(self._emails_notificacao)
        except json.JSONDecodeError:
            return []
    
    @emails_notificacao.setter
    def emails_notificacao(self, value):
        """Define a lista de emails para notificação."""
        try:
            if isinstance(value, list):
                self._emails_notificacao = json.dumps(value)
            elif isinstance(value, str):
                # Se for uma string única, converte para lista
                emails = [email.strip() for email in value.split(',') if email.strip()]
                self._emails_notificacao = json.dumps(emails)
            else:
                self._emails_notificacao = json.dumps([])
        except Exception:
            self._emails_notificacao = json.dumps([])
    
    @property
    def prazos_notificacao(self):
        """Retorna a lista de prazos de notificação."""
        if not self._prazos_notificacao:
            return []
        try:
            return json.loads(self._prazos_notificacao)
        except json.JSONDecodeError:
            return []
    
    @prazos_notificacao.setter
    def prazos_notificacao(self, value):
        """Define a lista de prazos de notificação."""
        try:
            if isinstance(value, list):
                self._prazos_notificacao = json.dumps(value)
            elif isinstance(value, str):
                # Se for uma string, tenta converter para lista
                try:
                    prazos = [int(prazo.strip()) for prazo in value.split(',') if prazo.strip()]
                    self._prazos_notificacao = json.dumps(prazos)
                except ValueError:
                    self._prazos_notificacao = json.dumps([30])  # Valor padrão
            else:
                self._prazos_notificacao = json.dumps([30])  # Valor padrão
        except Exception:
            self._prazos_notificacao = json.dumps([30])
    
    @property
    def esta_vencido(self):
        """Verifica se o documento está vencido."""
        if not self.data_vencimento:
            return False
        return datetime.date.today() > self.data_vencimento
    
    @property
    def proximo_vencimento(self):
        """Calcula quantos dias faltam para o vencimento."""
        if not self.data_vencimento:
            return None
        dias = (self.data_vencimento - datetime.date.today()).days
        return dias
    
    @property
    def precisa_notificar(self):
        """Verifica se é necessário notificar sobre o vencimento."""
        if not self.data_vencimento:
            return False
        dias = self.proximo_vencimento
        if dias is None:
            return False
        
        # Verifica se o número de dias está em algum dos prazos de notificação
        return dias >= 0 and dias in self.prazos_notificacao
    
    @property
    def entidade_relacionada(self):
        """Retorna a entidade relacionada (fazenda ou pessoa)."""
        if self.tipo_entidade == TipoEntidade.FAZENDA:
            return self.fazenda
        else:
            return self.pessoa
    
    @property
    def nome_entidade(self):
        """Retorna o nome da entidade relacionada."""
        entidade = self.entidade_relacionada
        return entidade.nome if entidade else "Não definido"
