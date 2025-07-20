# /src/routes/auth.py

from flask import Blueprint, flash, redirect, render_template, request, url_for, current_app
from flask_login import login_user, logout_user, login_required, current_user
import secrets
from datetime import datetime, timedelta

from src.models.db import db
from src.models.usuario import Usuario

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Rota para autenticação de usuários"""
    if current_user.is_authenticated:
        return redirect(url_for("admin.index"))
        
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        senha = request.form.get("senha", "")
        lembrar = 'lembrar' in request.form

        usuario = Usuario.query.filter_by(email=email).first()
        if usuario and usuario.check_password(senha):
            login_user(usuario, remember=lembrar)
            usuario.ultimo_login = datetime.utcnow()
            db.session.commit()
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for("admin.index"))
        else:
            flash("Usuário ou senha inválidos", "danger")

    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip()
        senha = request.form.get("senha", "")
        senha_confirmacao = request.form.get("senha_confirmacao", "")

        # Validação básica
        if not nome or not email or not senha or not senha_confirmacao:
            flash("Todos os campos são obrigatórios!", "danger")
            return render_template("register.html")
        if len(senha) < 5:
            flash("A senha deve ter pelo menos 5 caracteres.", "danger")
            return render_template("register.html")
        if senha != senha_confirmacao:
            flash("As senhas não conferem!", "danger")
            return render_template("register.html")
        if Usuario.query.filter_by(email=email).first():
            flash("E-mail já cadastrado!", "danger")
            return render_template("register.html")

        # Permite senha simples de qualquer tipo, a partir de 5 caracteres
        novo_usuario = Usuario(
            nome=nome,
            email=email,
            ativo=True  # criado_em já é automático no modelo
        )
        novo_usuario.set_password(senha)
        db.session.add(novo_usuario)
        db.session.commit()

        flash("Usuário cadastrado com sucesso! Faça login.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """Rota para logout de usuários"""
    logout_user()
    flash("Logout realizado com sucesso!", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/esqueci-senha", methods=["GET", "POST"])
def esqueci_senha():
    """Rota para recuperação de senha"""
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        usuario = Usuario.query.filter_by(email=email).first()
        if usuario:
            token = secrets.token_urlsafe(32)
            usuario.token_recuperacao = token
            usuario.token_expiracao = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()
            try:
                from src.utils.email_service import enviar_email
                link_recuperacao = url_for('auth.redefinir_senha', token=token, _external=True)
                assunto = "Recuperação de Senha - Sistema de Gestão Agrícola"
                corpo = f"""
                <h2>Recuperação de Senha</h2>
                <p>Olá {usuario.nome},</p>
                <p>Recebemos uma solicitação para redefinir sua senha.</p>
                <p>Se foi você quem solicitou, clique no link abaixo para criar uma nova senha:</p>
                <p><a href="{link_recuperacao}">Redefinir minha senha</a></p>
                <p>Este link expira em 1 hora.</p>
                <p>Se não foi você quem solicitou, ignore este email.</p>
                <p>Atenciosamente,<br>Equipe do Sistema de Gestão Agrícola</p>
                """
                enviar_email(email, assunto, corpo)
                flash("Instruções para recuperação de senha foram enviadas para seu email.", "success")
            except Exception as e:
                current_app.logger.error(f"Erro ao enviar email de recuperação: {e}")
                flash("Ocorreu um erro ao processar seu pedido. Por favor, tente novamente.", "danger")
        else:
            flash("Se este email estiver cadastrado, enviaremos instruções de recuperação.", "info")
        return redirect(url_for("auth.login"))
    return render_template("esqueci_senha.html")


@auth_bp.route("/redefinir-senha/<token>", methods=["GET", "POST"])
def redefinir_senha(token):
    """Rota para redefinição de senha com token"""
    usuario = Usuario.query.filter_by(token_recuperacao=token).first()
    if not usuario or not usuario.token_expiracao or usuario.token_expiracao < datetime.utcnow():
        flash("O link de recuperação é inválido ou expirou.", "danger")
        return redirect(url_for("auth.esqueci_senha"))
    if request.method == "POST":
        nova_senha = request.form.get("senha", "")
        confirmacao = request.form.get("senha_confirmacao", "")
        if not nova_senha or not confirmacao:
            flash("Preencha ambos os campos de senha.", "danger")
            return render_template("redefinir_senha.html", token=token)
        if len(nova_senha) < 5:
            flash("A nova senha deve ter pelo menos 5 caracteres.", "danger")
            return render_template("redefinir_senha.html", token=token)
        if nova_senha != confirmacao:
            flash("As senhas não conferem!", "danger")
            return render_template("redefinir_senha.html", token=token)
        usuario.set_password(nova_senha)
        usuario.token_recuperacao = None
        usuario.token_expiracao = None
        db.session.commit()
        flash("Sua senha foi redefinida com sucesso! Faça login com a nova senha.", "success")
        return redirect(url_for("auth.login"))
    return render_template("redefinir_senha.html", token=token)


@auth_bp.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    """Rota para visualização e edição do perfil do usuário"""
    usuario = current_user
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip()
        senha_atual = request.form.get("senha_atual", "")
        nova_senha = request.form.get("nova_senha", "")

        if not nome or not email:
            flash("Nome e email são obrigatórios!", "danger")
        else:
            usuario_existente = Usuario.query.filter_by(email=email).first()
            if usuario_existente and usuario_existente.id != usuario.id:
                flash("Este email já está em uso por outro usuário.", "danger")
            else:
                usuario.nome = nome
                usuario.email = email
                if senha_atual and nova_senha:
                    if usuario.check_password(senha_atual):
                        if len(nova_senha) < 5:
                            flash("A nova senha deve ter pelo menos 5 caracteres.", "danger")
                        else:
                            usuario.set_password(nova_senha)
                            flash("Senha atualizada com sucesso!", "success")
                    else:
                        flash("Senha atual incorreta!", "danger")
                db.session.commit()
                flash("Perfil atualizado com sucesso!", "success")
    return render_template("perfil.html", usuario=usuario)