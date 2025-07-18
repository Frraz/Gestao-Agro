# /src/utils/database.py

"""
Database utility functions for common operations.
"""

from datetime import datetime, date
from math import ceil
from typing import Tuple, Type, Any, Optional

from flask import flash
from sqlalchemy.orm import Query

from src.models.db import db


def paginate_query(query: Query, page: int = 1, per_page: int = 10) -> Tuple[list, int, int]:
    """
    Paginate a SQLAlchemy query.

    Args:
        query: SQLAlchemy query object
        page: Page number (1-based)
        per_page: Number of items per page

    Returns:
        Tuple of (items, total_count, total_pages)
    """
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    total_pages = ceil(total / per_page) if total else 1

    return items, total, total_pages


def safe_count(model: Type[db.Model]) -> int:
    """
    Safely count records in a model table.

    Args:
        model: SQLAlchemy model class

    Returns:
        Number of records or 0 if error
    """
    try:
        return model.query.count()
    except Exception:
        return 0


def safe_add_and_commit(obj: Any) -> bool:
    """
    Safely add an object to database and commit.

    Args:
        obj: Database object to add

    Returns:
        True if successful, False otherwise
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
    Safely commit current database session.

    Returns:
        True if successful, False otherwise
    """
    try:
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False


def safe_delete_and_commit(obj: Any) -> bool:
    """
    Safely delete an object from database and commit.

    Args:
        obj: Database object to delete

    Returns:
        True if successful, False otherwise
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
    Safely parse a string to float with user feedback.

    Args:
        value: String value to parse
        field_name: Name of the field for error message

    Returns:
        Float value or None if parsing fails
    """
    try:
        return float(value)
    except ValueError:
        flash(f"O campo '{field_name}' deve ser um número válido.", "danger")
        return None


def safe_parse_date(value: str, field_name: str = "data") -> Optional[date]:
    """
    Safely parse a string to date with user feedback.

    Args:
        value: String value in format YYYY-MM-DD
        field_name: Name of the field for error message

    Returns:
        Date object or None if parsing fails
    """
    if not value:
        return None

    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        flash(f"O campo '{field_name}' deve estar no formato AAAA-MM-DD.", "danger")
        return None
