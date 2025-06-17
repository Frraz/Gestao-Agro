#/src/models/fazenda.py

from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Table, Enum, Index
from sqlalchemy.orm import relationship
from src.models.db import db
from src.models.pessoa import pessoa_fazenda
import enum
import datetime

class TipoPosse(enum.Enum):
    PROPRIA = "Própria"
    ARRENDADA = "Arrendada"
    COMODATO = "Comodato"
    POSSE = "Posse"

class Fazenda(db.Model):
    """
    Modelo para cadastro de fazendas/áreas que podem ser associadas a uma ou mais pessoas.
    """
    __tablename__ = 'fazenda'
    
    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False, index=True)
    matricula = Column(String(50), unique=True, nullable=False, index=True)
    tamanho_total = Column(Float, nullable=False)  # em hectares
    area_consolidada = Column(Float, nullable=False)  # em hectares (anteriormente tamanho_usado)
    tamanho_disponivel = Column(Float, nullable=False)  # em hectares (calculado automaticamente)
    tipo_posse = Column(Enum(TipoPosse), nullable=False, index=True)
    municipio = Column(String(100), nullable=False, index=True)
    estado = Column(String(2), nullable=False, index=True)
    recibo_car = Column(String(100), nullable=True)  # Número do recibo do CAR (opcional)
    
    # Campos de auditoria
    data_criacao = Column(db.Date, default=datetime.date.today, nullable=False)
    data_atualizacao = Column(db.Date, default=datetime.date.today, onupdate=datetime.date.today, nullable=False)
    
    # Relacionamento muitos-para-muitos com Pessoa (otimizado)
    pessoas = relationship('Pessoa', secondary=pessoa_fazenda, back_populates='fazendas', lazy='selectin')
    
    # Relacionamento um-para-muitos com Documento (otimizado)
    documentos = relationship('Documento', back_populates='fazenda', cascade='all, delete-orphan', lazy='selectin')
    
    # Índices compostos para consultas frequentes
    __table_args__ = (
        Index('idx_fazenda_estado_municipio', 'estado', 'municipio'),
        Index('idx_fazenda_tipo_posse', 'tipo_posse'),
    )
    
    def __repr__(self):
        return f'<Fazenda {self.nome} - {self.matricula}>'
    
    @property
    def calcular_tamanho_disponivel(self):
        """Calcula o tamanho disponível com base no tamanho total e área consolidada."""
        return self.tamanho_total - self.area_consolidada
    
    def atualizar_tamanho_disponivel(self):
        """Atualiza o campo tamanho_disponivel com base nos valores atuais."""
        self.tamanho_disponivel = self.calcular_tamanho_disponivel
        return self.tamanho_disponivel
    
    @property
    def total_documentos(self):
        """Retorna o número total de documentos associados à fazenda."""
        return len(self.documentos) if self.documentos else 0
    
    @property
    def documentos_vencidos(self):
        """Retorna a lista de documentos vencidos."""
        return [doc for doc in self.documentos if doc.esta_vencido]
    
    @property
    def documentos_a_vencer(self):
        """Retorna a lista de documentos próximos do vencimento."""
        return [doc for doc in self.documentos if not doc.esta_vencido and doc.precisa_notificar]
