# /src/models/db.py

"""
Módulo responsável por inicializar a instância do SQLAlchemy para o projeto.

A variável `db` é utilizada nos modelos para mapear as tabelas do banco de dados.
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()