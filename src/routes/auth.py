from flask import Blueprint, request, redirect, url_for, render_template, flash
from flask_login import login_user
from src.models.usuario import Usuario

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        usuario = Usuario.query.filter_by(email=email).first()
        if usuario and usuario.check_password(senha):
            login_user(usuario)
            return redirect(url_for('home'))  # Troque 'home' para sua rota principal
        else:
            flash('Usuário ou senha inválidos')
    return render_template('login.html')