from flask import Blueprint, request, redirect, url_for, render_template, flash
from flask_login import login_user, logout_user
from src.models.usuario import Usuario
from src.models.db import db

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')

        usuario = Usuario.query.filter_by(email=email).first()
        if usuario and usuario.check_password(senha):
            login_user(usuario)
            return redirect(url_for('home'))  # Substitua 'home' pela sua rota principal real
        else:
            flash('Usuário ou senha inválidos', 'danger')

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        senha = request.form.get('senha')

        if Usuario.query.filter_by(email=email).first():
            flash('E-mail já cadastrado!', 'danger')
            return render_template('register.html')

        novo_usuario = Usuario(nome=nome, email=email)
        novo_usuario.set_password(senha)

        db.session.add(novo_usuario)
        db.session.commit()

        flash('Usuário cadastrado com sucesso! Faça login.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')
