# /src/utils/endividamento_area_utils.py

from src.models.db import db
from src.models.endividamento_area import EndividamentoArea
from src.models.area import Area


def adicionar_areas_endividamento(endividamento_id, lista_areas):
    """
    Remove vínculos antigos e cria novos entre endividamento e áreas.
    lista_areas = [
        {"area_id": 1, "tipo": "objeto_credito", "hectares_utilizados": 50.0},
        {"area_id": 2, "tipo": "garantia", "hectares_utilizados": None}
    ]
    """
    # Remove os vínculos antigos desse endividamento
    EndividamentoArea.query.filter_by(endividamento_id=endividamento_id).delete()
    db.session.commit()
    # Adiciona novos vínculos
    for area in lista_areas:
        vinculo = EndividamentoArea(
            endividamento_id=endividamento_id,
            area_id=area["area_id"],
            tipo=area["tipo"],
            hectares_utilizados=area.get("hectares_utilizados"),
        )
        db.session.add(vinculo)
    db.session.commit()


def get_areas_vinculadas(endividamento_id):
    vinculos = EndividamentoArea.query.filter_by(endividamento_id=endividamento_id).all()
    return [v.to_dict() for v in vinculos]


def remover_area_vinculo(endividamento_id, area_id):
    EndividamentoArea.query.filter_by(endividamento_id=endividamento_id, area_id=area_id).delete()
    db.session.commit()


def validar_hectares_disponiveis(area_id, hectares_solicitados):
    area = Area.query.get(area_id)
    if not area:
        return False, "Área não encontrada."
    # Supondo que area.tamanho_disponivel está atualizado
    if hectares_solicitados and hectares_solicitados > area.tamanho_disponivel:
        return False, f"Área disponível insuficiente ({area.tamanho_disponivel} ha disponíveis)."
    return True, ""


def listar_areas_disponiveis(fazenda_id):
    return Area.query.filter_by(fazenda_id=fazenda_id).filter(Area.tamanho_disponivel > 0).all()
