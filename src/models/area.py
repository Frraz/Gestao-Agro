# /src/models/area.py

"""
Modelo para cadastro de áreas específicas dentro de uma fazenda.

Cada área está vinculada a uma fazenda e pode ser utilizada para controle de endividamentos ou categorização (ex: consolidada, disponível etc).
"""

from src.models.db import db

class Area(db.Model):
    __tablename__ = "area"
    id = db.Column(db.Integer, primary_key=True)
    fazenda_id = db.Column(db.Integer, db.ForeignKey("fazenda.id", ondelete="CASCADE"), nullable=False, index=True)
    nome = db.Column(db.String(255), nullable=False, index=True)
    hectares = db.Column(db.Numeric(10, 2), nullable=False)
    tipo = db.Column(db.String(50), nullable=False, index=True)  # exemplo: 'consolidada', 'disponivel', etc.

    # Relacionamentos
    fazenda = db.relationship("Fazenda", back_populates="areas", lazy="joined")
    endividamentos_vinculados = db.relationship(
        "EndividamentoArea", back_populates="area", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self):
        return f"<Area {self.nome} - {self.hectares} ha>"

    def to_dict(self):
        return {
            "id": self.id,
            "fazenda_id": self.fazenda_id,
            "nome": self.nome,
            "hectares": float(self.hectares),
            "tipo": self.tipo,
        }