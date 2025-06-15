# Formulários para Endividamentos
from flask_wtf import FlaskForm
from wtforms import StringField, DateField, DecimalField, SelectField, IntegerField, TextAreaField, FieldList, FormField, HiddenField
from wtforms.validators import DataRequired, NumberRange, Optional, Length
from wtforms.widgets import TextArea
from datetime import date

class ParcelaForm(FlaskForm):
    """Formulário para cadastro de parcelas"""
    id = HiddenField()
    data_vencimento = DateField('Data de Vencimento', validators=[DataRequired()])
    valor = DecimalField('Valor (R$)', validators=[DataRequired(), NumberRange(min=0.01)], places=2)
    
class EndividamentoFazendaForm(FlaskForm):
    """Formulário para vínculo com fazendas"""
    id = HiddenField()
    fazenda_id = SelectField('Fazenda', coerce=int, validators=[Optional()])
    hectares = DecimalField('Hectares', validators=[Optional(), NumberRange(min=0)], places=2)
    tipo = SelectField('Tipo', choices=[('objeto_credito', 'Objeto do Crédito'), ('garantia', 'Garantia')], validators=[DataRequired()])
    descricao = TextAreaField('Descrição Livre', validators=[Optional(), Length(max=1000)])

class EndividamentoForm(FlaskForm):
    """Formulário principal para cadastro de endividamentos"""
    banco = StringField('Banco', validators=[DataRequired(), Length(max=255)])
    numero_proposta = StringField('Número da Proposta', validators=[DataRequired(), Length(max=255)])
    data_emissao = DateField('Data de Emissão', validators=[DataRequired()])
    data_vencimento_final = DateField('Data de Vencimento Final', validators=[DataRequired()])
    taxa_juros = DecimalField('Taxa de Juros (%)', validators=[DataRequired(), NumberRange(min=0)], places=4)
    tipo_taxa_juros = SelectField('Tipo da Taxa', choices=[('ano', 'Ao Ano'), ('mes', 'Ao Mês')], validators=[DataRequired()])
    prazo_carencia = IntegerField('Prazo de Carência (meses)', validators=[Optional(), NumberRange(min=0)])
    valor_operacao = DecimalField('Valor da Operação (R$)', validators=[Optional(), NumberRange(min=0)], places=2)
    
    # Campos para seleção de pessoas (será preenchido dinamicamente)
    pessoas_selecionadas = StringField('Pessoas Selecionadas')
    
    def validate_data_vencimento_final(self, field):
        """Valida se a data de vencimento final é posterior à data de emissão"""
        if field.data and self.data_emissao.data:
            if field.data <= self.data_emissao.data:
                raise ValidationError('A data de vencimento final deve ser posterior à data de emissão.')

class FiltroEndividamentoForm(FlaskForm):
    """Formulário para filtros na listagem de endividamentos"""
    banco = StringField('Banco')
    pessoa_id = SelectField('Pessoa', coerce=int, validators=[Optional()])
    fazenda_id = SelectField('Fazenda', coerce=int, validators=[Optional()])
    data_inicio = DateField('Data de Emissão - De', validators=[Optional()])
    data_fim = DateField('Data de Emissão - Até', validators=[Optional()])
    vencimento_inicio = DateField('Vencimento - De', validators=[Optional()])
    vencimento_fim = DateField('Vencimento - Até', validators=[Optional()])

