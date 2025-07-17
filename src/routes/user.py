# /src/routes/user.py

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.models.user import User, db

user_bp = Blueprint("user", __name__)

@user_bp.route("/users", methods=["GET"])
def get_users():
    """Lista todos os usuários."""
    try:
        users = User.query.all()
        return jsonify([user.to_dict() for user in users])
    except Exception as e:
        return jsonify({"erro": f"Erro ao listar usuários: {str(e)}"}), 500

@user_bp.route("/users", methods=["POST"])
def create_user():
    """Cria um novo usuário."""
    try:
        data = request.json
        if not data or not data.get("username") or not data.get("email"):
            return jsonify({"erro": "Username e email são obrigatórios"}), 400

        # Verifica se já existe usuário com o mesmo email
        if User.query.filter_by(email=data["email"]).first():
            return jsonify({"erro": "E-mail já cadastrado"}), 400

        user = User(username=data["username"], email=data["email"])
        db.session.add(user)
        db.session.commit()
        return jsonify(user.to_dict()), 201
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({"erro": f"Erro de integridade: {str(e)}"}), 400
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"erro": f"Erro de banco de dados: {str(e)}"}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": f"Erro ao criar usuário: {str(e)}"}), 500

@user_bp.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    """Obtém detalhes de um usuário específico."""
    try:
        user = User.query.get_or_404(user_id)
        return jsonify(user.to_dict())
    except Exception as e:
        return jsonify({"erro": f"Erro ao obter usuário: {str(e)}"}), 500

@user_bp.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    """Atualiza os dados de um usuário."""
    try:
        user = User.query.get_or_404(user_id)
        data = request.json
        if not data:
            return jsonify({"erro": "Dados não fornecidos"}), 400

        if "username" in data and data["username"]:
            user.username = data["username"]
        if "email" in data and data["email"]:
            # Checa se o email já está em uso por outro usuário
            existing = User.query.filter_by(email=data["email"]).first()
            if existing and existing.id != user.id:
                return jsonify({"erro": "E-mail já cadastrado para outro usuário"}), 400
            user.email = data["email"]
        db.session.commit()
        return jsonify(user.to_dict())
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({"erro": f"Erro de integridade: {str(e)}"}), 400
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"erro": f"Erro de banco de dados: {str(e)}"}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": f"Erro ao atualizar usuário: {str(e)}"}), 500

@user_bp.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    """Exclui um usuário."""
    try:
        user = User.query.get_or_404(user_id)
        db.session.delete(user)
        db.session.commit()
        return "", 204
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"erro": f"Erro de banco de dados ao excluir usuário: {str(e)}"}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"erro": f"Erro ao excluir usuário: {str(e)}"}), 500