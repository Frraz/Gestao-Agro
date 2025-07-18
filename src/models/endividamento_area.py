# /src/models/endividamento_area.py

"""
Modelo de vínculo entre endividamento e área específica de uma fazenda.
"""

from datetime import datetime
from typing import Dict, Any

from src.models.db import db


class EndividamentoArea(db.Model):
    """
    Modelo de vínculo entre endividamento e área específica de uma fazenda.
    
    Permite vincular um endividamento a áreas específicas dentro de uma fazenda,
    com hectares e propósito específicos.
    """
    __tablename__ = "endividamento_area"
    __table_args__ = {'extend_existing': True}  # Permite redefinição da tabela para evitar conflitos

    id = db.Column(db.Integer, primary_key=True)
    endividamento_id = db.Column(
        db.Integer, db.ForeignKey("endividamento.id"), nullable=False
    )
    area_id = db.Column(
        db.Integer, db.ForeignKey("area.id"), nullable=False
    )
    hectares_utilizados = db.Column(db.Numeric(10, 2), nullable=True)
    tipo = db.Column(
        db.String(50), nullable=False, default="objeto_credito"
    )  # 'objeto_credito' ou 'garantia'
    descricao = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # É importante usar o mesmo nome de relação que está em Endividamento
    endividamento = db.relationship("Endividamento", back_populates="area_vinculos")
    area = db.relationship("Area")

    def __repr__(self) -> str:
        return f'<EndividamentoArea {self.tipo} - {self.area.nome if self.area else "Desconhecida"}>'

    def to_dict(self) -> Dict[str, Any]:
        """
        Converte o vínculo de área para um dicionário.
        
        Returns:
            Dicionário com os dados do vínculo
        """
        return {
            "id": self.id,
            "endividamento_id": self.endividamento_id,
            "area_id": self.area_id,
            "area_nome": self.area.nome if self.area else None,
            "hectares_utilizados": float(self.hectares_utilizados) if self.hectares_utilizados else None,
            "tipo": self.tipo,
            "hectares_utilizados": float(self.hectares_utilizados) if self.hectares_utilizados else None
        }
