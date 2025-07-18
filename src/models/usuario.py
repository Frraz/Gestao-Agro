# /src/models/usuario.py

"""
Modelo unificado para cadastro e autenticação de usuários do sistema.

Inclui username, email (ambos únicos), senha segura (hash) e integração com Flask-Login.
"""

from datetime import datetime
from typing import Optional

from werkzeug.security import check_password_hash, generate_password_hash

from src.models.db import db


class Usuario(db.Model):  # type: ignore
    """
    Modelo para usuários autenticáveis do sistema.

    Attributes:
        id (int): Identificador do usuário.
        nome (str): Nome completo do usuário.
        username (str): Nome de usuário único (opcional, se desejar login por nome de usuário).
        email (str): Email do usuário (único).
        senha_hash (str): Hash da senha.
        criado_em (datetime): Data de criação do usuário.
    """

    __tablename__ = "usuario"

    id: int = db.Column(db.Integer, primary_key=True)
    nome: str = db.Column(db.String(100), nullable=False)
    username: Optional[str] = db.Column(
        db.String(80), unique=True, nullable=True
    )  # Deixe nullable=True se opcional
    email: str = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash: str = db.Column(db.String(512), nullable=False)
    criado_em: datetime = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, senha: str) -> None:
        """Define a senha do usuário (armazenando o hash)."""
        self.senha_hash = generate_password_hash(senha)

    def check_password(self, senha: str) -> bool:
        """Verifica se a senha informada está correta."""
        return check_password_hash(self.senha_hash, senha)

    @property
    def is_authenticated(self) -> bool:
        """Indica se o usuário está autenticado (integração com Flask-Login)."""
        return True

    @property
    def is_active(self) -> bool:
        """Indica se o usuário está ativo (integração com Flask-Login)."""
        return True

    @property
    def is_anonymous(self) -> bool:
        """Indica se o usuário é anônimo (integração com Flask-Login)."""
        return False

    def get_id(self) -> str:
        """Retorna o ID do usuário como string (para Flask-Login)."""
        return str(self.id)

    def __repr__(self) -> str:
        return f"<Usuario {self.username or self.email}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nome": self.nome,
            "username": self.username,
            "email": self.email,
        }
