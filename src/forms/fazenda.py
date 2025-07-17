# from flask_wtf import FlaskForm

from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SelectField, FieldList, FormField, DateField
from wtforms.validators import DataRequired, Optional
from src.models.pessoa_fazenda import TipoPosse

class PessoaFazendaForm(FlaskForm):
    pessoa_id = SelectField('Pessoa', coerce=int, validators=[DataRequired()])
    tipo_posse = SelectField(
        'Tipo de Posse',
        choices=[(tipo.name, tipo.value) for tipo in TipoPosse],
        validators=[Optional()]
    )

class FazendaForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired()])
    matricula = StringField('Matrícula', validators=[DataRequired()])
    tamanho_total = FloatField('Tamanho Total (ha)', validators=[DataRequired()])
    area_consolidada = FloatField('Área Consolidada (ha)', validators=[DataRequired()])
    tamanho_disponivel = FloatField('Tamanho Disponível (ha)', validators=[DataRequired()])
    municipio = StringField('Município', validators=[DataRequired()])
    estado = StringField('Estado', validators=[DataRequired()])
    pessoas_fazenda = FieldList(FormField(PessoaFazendaForm), min_entries=1)