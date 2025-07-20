# /src/models/area.py

from src.models.db import db

class Area(db.Model):
    __tablename__ = "area"
    id = db.Column(db.Integer, primary_key=True)
    fazenda_id = db.Column(db.Integer, db.ForeignKey("fazenda.id"), nullable=False)
    nome = db.Column(db.String(255), nullable=False)
    hectares = db.Column(db.Numeric(10, 2), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)  # exemplo: 'consolidada', 'disponivel', etc.

    # Relacionamentos
    fazenda = db.relationship("Fazenda", back_populates="areas")
    endividamentos_vinculados = db.relationship(
        "EndividamentoArea", back_populates="area", cascade="all, delete-orphan"
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