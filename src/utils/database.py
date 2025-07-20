# /src/utils/database.py

"""
Funções utilitárias para operações comuns de banco de dados.
"""

from datetime import datetime, date
from math import ceil
from typing import Tuple, Type, Any, Optional

from flask import flash
from sqlalchemy.orm import Query
from src.models.db import db


def paginate_query(query: Query, page: int = 1, per_page: int = 10) -> Tuple[list, int, int]:
    """
    Pagina uma query do SQLAlchemy.

    Args:
        query: Objeto Query do SQLAlchemy
        page: Número da página (base 1)
        per_page: Itens por página

    Returns:
        Tupla (itens, total_de_registros, total_de_paginas)
    """
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    total_pages = ceil(total / per_page) if total else 1
    return items, total, total_pages


def safe_count(model: Type[Any]) -> int:
    """
    Conta registros em uma tabela do modelo, com fallback seguro.

    Args:
        model: Classe do modelo SQLAlchemy

    Returns:
        Número de registros ou 0 em caso de erro.
    """
    try:
        return model.query.count()
    except Exception:
        return 0


def safe_add_and_commit(obj: Any) -> bool:
    """
    Adiciona e commita um objeto ao banco de dados de forma segura.

    Args:
        obj: Objeto a ser adicionado

    Returns:
        True em caso de sucesso, False caso contrário.
    """
    try:
        db.session.add(obj)
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False


def safe_commit() -> bool:
    """
    Faz commit da sessão atual de forma segura.

    Returns:
        True em caso de sucesso, False caso contrário.
    """
    try:
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False


def safe_delete_and_commit(obj: Any) -> bool:
    """
    Remove e commita um objeto do banco de dados de forma segura.

    Args:
        obj: Objeto a ser removido

    Returns:
        True em caso de sucesso, False caso contrário.
    """
    try:
        db.session.delete(obj)
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False


def safe_parse_float(value: str, field_name: str = "valor") -> Optional[float]:
    """
    Tenta converter uma string para float, mostrando mensagem de erro se falhar.

    Args:
        value: Valor string a ser convertido
        field_name: Nome do campo para exibir em caso de erro

    Returns:
        Valor float ou None se falhar.
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        flash(f"O campo '{field_name}' deve ser um número válido.", "danger")
        return None


def safe_parse_date(value: str, field_name: str = "data") -> Optional[date]:
    """
    Tenta converter uma string para date no formato YYYY-MM-DD.

    Args:
        value: Valor string no formato AAAA-MM-DD
        field_name: Nome do campo para exibir em caso de erro

    Returns:
        Objeto date ou None se falhar.
    """
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        flash(f"O campo '{field_name}' deve estar no formato AAAA-MM-DD.", "danger")
        return None
    