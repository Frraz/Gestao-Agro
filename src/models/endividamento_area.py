# /src/models/endividamento_area.py

from src.models.db import db


class EndividamentoArea(db.Model):
    __tablename__ = "endividamento_area"
    id = db.Column(db.Integer, primary_key=True)
    endividamento_id = db.Column(db.Integer, db.ForeignKey("endividamento.id"), nullable=False)
    area_id = db.Column(db.Integer, db.ForeignKey("area.id"), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)  # 'objeto_credito' ou 'garantia'
    hectares_utilizados = db.Column(db.Numeric(10, 2), nullable=True)  # só preenche se objeto_credito

    endividamento = db.relationship("Endividamento", back_populates="area_vinculos")
    area = db.relationship("Area", back_populates="endividamentos_vinculados")

    def __repr__(self):
        return f"<EndividamentoArea {self.tipo} - {self.area.nome if self.area else '-'} ({self.hectares_utilizados or '-'} ha)>"

    def to_dict(self):
        return {
            "id": self.id,
            "endividamento_id": self.endividamento_id,
            "area_id": self.area_id,
            "area_nome": self.area.nome if self.area else None,
            "tipo": self.tipo,
            "hectares_utilizados": float(self.hectares_utilizados) if self.hectares_utilizados else None
        }
