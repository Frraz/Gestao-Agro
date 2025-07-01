# /src/forms/endividamento.py

from flask_wtf import FlaskForm
from wtforms import (
    DateField, DecimalField, HiddenField, IntegerField, SelectField, StringField,
    TextAreaField
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional, ValidationError

class EndividamentoForm(FlaskForm):
    """Formulário principal para cadastro de endividamentos"""

    banco = StringField("Banco", validators=[DataRequired(), Length(max=255)])
    numero_proposta = StringField(
        "Número da Proposta", validators=[DataRequired(), Length(max=255)]
    )
    data_emissao = DateField("Data de Emissão", validators=[DataRequired()])
    data_vencimento_final = DateField(
        "Data de Vencimento Final", validators=[DataRequired()]
    )
    taxa_juros = DecimalField(
        "Taxa de Juros (%)", validators=[DataRequired(), NumberRange(min=0)], places=4
    )
    tipo_taxa_juros = SelectField(
        "Tipo da Taxa",
        choices=[("ano", "Ao Ano"), ("mes", "Ao Mês")],
        validators=[DataRequired()],
    )
    prazo_carencia = IntegerField(
        "Prazo de Carência (meses)", validators=[Optional(), NumberRange(min=0)]
    )
    valor_operacao = DecimalField(
        "Valor da Operação (R$)", validators=[Optional(), NumberRange(min=0)], places=2
    )

    pessoas_selecionadas = StringField("Pessoas Selecionadas")

    # Campos hidden para as listas (em JSON)
    objetos_credito = HiddenField("Áreas de Crédito (JSON)")
    garantias = HiddenField("Garantias (JSON)")
    parcelas = HiddenField("Parcelas (JSON)")

    def validate_data_vencimento_final(self, field):
        if field.data and self.data_emissao.data:
            if field.data <= self.data_emissao.data:
                raise ValidationError(
                    "A data de vencimento final deve ser posterior à data de emissão."
                )

class FiltroEndividamentoForm(FlaskForm):
    banco = StringField("Banco")
    pessoa_id = SelectField("Pessoa", coerce=int, validators=[Optional()])
    fazenda_id = SelectField("Fazenda", coerce=int, validators=[Optional()])
    data_inicio = DateField("Data de Emissão - De", validators=[Optional()])
    data_fim = DateField("Data de Emissão - Até", validators=[Optional()])
    vencimento_inicio = DateField("Vencimento - De", validators=[Optional()])
    vencimento_fim = DateField("Vencimento - Até", validators=[Optional()])