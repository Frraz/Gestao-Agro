# /src/utils/api_responses.py

"""
Utility functions for standardized API responses.
"""

from datetime import datetime
from typing import Any, Dict, Optional, Union

from flask import jsonify


def success_response(
    data: Any = None,
    message: str = "Operação realizada com sucesso",
    status_code: int = 200
) -> tuple:
    """
    Create a standardized success response.

    Args:
        data: Response data
        message: Success message
        status_code: HTTP status code

    Returns:
        Tuple of (response, status_code)
    """
    response = {
        "status": "success",
        "message": message,
        "timestamp": datetime.now().isoformat()
    }

    if data is not None:
        response["data"] = data

    return jsonify(response), status_code


def error_response(
    error: str,
    status_code: int = 400,
    details: Optional[Dict[str, Any]] = None
) -> tuple:
    """
    Create a standardized error response.

    Args:
        error: Error message
        status_code: HTTP status code
        details: Additional error details

    Returns:
        Tuple of (response, status_code)
    """
    response = {
        "status": "error",
        "error": error,
        "timestamp": datetime.now().isoformat()
    }

    if details:
        response["details"] = details

    return jsonify(response), status_code


def validation_error_response(
    errors: Union[str, Dict[str, Any]],
    status_code: int = 422
) -> tuple:
    """
    Create a standardized validation error response.

    Args:
        errors: Validation errors
        status_code: HTTP status code

    Returns:
        Tuple of (response, status_code)
    """
    return error_response(
        error="Dados inválidos",
        status_code=status_code,
        details={"validation_errors": errors}
    )


def not_found_response(resource: str = "Recurso") -> tuple:
    """
    Create a standardized not found response.

    Args:
        resource: Name of the resource not found

    Returns:
        Tuple of (response, status_code)
    """
    return error_response(
        error=f"{resource} não encontrado",
        status_code=404
    )


def unauthorized_response(message: str = "Acesso não autorizado") -> tuple:
    """
    Create a standardized unauthorized response.

    Args:
        message: Unauthorized message

    Returns:
        Tuple of (response, status_code)
    """
    return error_response(
        error=message,
        status_code=401
    )


def forbidden_response(message: str = "Acesso negado") -> tuple:
    """
    Create a standardized forbidden response.

    Args:
        message: Forbidden message

    Returns:
        Tuple of (response, status_code)
    """
    return error_response(
        error=message,
        status_code=403
    )


def server_error_response(message: str = "Erro interno do servidor") -> tuple:
    """
    Create a standardized server error response.

    Args:
        message: Error message

    Returns:
        Tuple of (response, status_code)
    """
    return error_response(
        error=message,
        status_code=500
    )
