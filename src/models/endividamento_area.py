# /src/models/endividamento_area.py

"""
Modelo de vínculo entre endividamento e área, permitindo indicar a utilização ou garantia de áreas específicas.
"""

from src.models.db import db

class EndividamentoArea(db.Model):
    __tablename__ = "endividamento_area"
    id = db.Column(db.Integer, primary_key=True)
    endividamento_id = db.Column(
        db.Integer,
        db.ForeignKey("endividamento.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    area_id = db.Column(
        db.Integer,
        db.ForeignKey("area.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    tipo = db.Column(db.String(50), nullable=False, index=True)  # 'objeto_credito' ou 'garantia'
    hectares_utilizados = db.Column(db.Numeric(10, 2), nullable=True)  # só preenche se objeto_credito

    endividamento = db.relationship("Endividamento", back_populates="area_vinculos", lazy="joined")
    area = db.relationship("Area", back_populates="endividamentos_vinculados", lazy="joined")

    def __repr__(self):
        return (
            f"<EndividamentoArea {self.tipo} - "
            f"{self.area.nome if self.area else '-'} ({self.hectares_utilizados or '-'} ha)>"
        )

    def to_dict(self):
        return {
            "id": self.id,
            "endividamento_id": self.endividamento_id,
            "area_id": self.area_id,
            "area_nome": self.area.nome if self.area else None,
            "tipo": self.tipo,
            "hectares_utilizados": float(self.hectares_utilizados) if self.hectares_utilizados else None
        }