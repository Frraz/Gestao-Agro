# src/forms/pessoa.py

from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired

class PessoaForm(FlaskForm):
    nome = StringField("Nome", validators=[DataRequired()])
    cpf_cnpj = StringField("CPF/CNPJ", validators=[DataRequired()])
    email = StringField("Email")
    telefone = StringField("Telefone")
    endereco = StringField("Endereço")