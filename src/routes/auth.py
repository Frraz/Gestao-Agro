# /src/routes/auth.py

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_user, logout_user, login_required

from src.models.db import db
from src.models.usuario import Usuario

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        senha = request.form.get("senha") or ""

        usuario = Usuario.query.filter_by(email=email).first()
        if usuario and usuario.check_password(senha):
            login_user(usuario)
            return redirect(url_for("admin.index"))
        else:
            flash("Usuário ou senha inválidos", "danger")

    return render_template("login.html")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        email = (request.form.get("email") or "").strip()
        senha = request.form.get("senha") or ""

        if not nome or not email or not senha:
            flash("Todos os campos são obrigatórios.", "danger")
            return render_template("register.html")

        if Usuario.query.filter_by(email=email).first():
            flash("E-mail já cadastrado!", "danger")
            return render_template("register.html")

        novo_usuario = Usuario(nome=nome, email=email)
        novo_usuario.set_password(senha)

        db.session.add(novo_usuario)
        db.session.commit()

        flash("Usuário cadastrado com sucesso! Faça login.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")

@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Logout realizado com sucesso!", "success")
    return redirect(url_for("auth.login"))