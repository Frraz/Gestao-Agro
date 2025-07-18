# /src/forms/notificacao_endividamento.py

"""Formulário para Notificações de Endividamento"""
from typing import List, Optional
from flask_wtf import FlaskForm
from wtforms import BooleanField, TextAreaField, SelectMultipleField, widgets, SubmitField
from wtforms.validators import DataRequired, Length, ValidationError
import re


class MultiCheckboxField(SelectMultipleField):
    """
    Campo customizado para múltiplos checkboxes.
    
    Permite selecionar múltiplas opções através de caixas de seleção
    em vez da interface padrão de seleção múltipla.
    """
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class NotificacaoEndividamentoForm(FlaskForm):
    """
    Formulário para configuração de notificações de endividamento.
    
    Permite configurar emails para receber notificações e 
    definir prazos para envio das notificações antes do vencimento.
    """

    emails = TextAreaField(
        "E-mails para Notificação",
        validators=[DataRequired(), Length(max=2000)],
        description="Digite um e-mail por linha. As notificações serão enviadas nos prazos selecionados abaixo.",
        render_kw={"rows": 5, "placeholder": "exemplo@email.com\noutro@email.com"}
    )
    
    prazos = MultiCheckboxField(
        "Prazos de Notificação",
        choices=[
            ('180', '6 meses antes'),
            ('90', '3 meses antes'),
            ('60', '60 dias antes'),
            ('30', '30 dias antes'),
            ('15', '15 dias antes'),
            ('7', '7 dias antes'),
            ('3', '3 dias antes'),
            ('1', '1 dia antes')
        ],
        default=['30', '15', '7', '3', '1'],  # Prazos padrão selecionados
        description="Selecione quando deseja receber as notificações"
    )
    
    ativo = BooleanField(
        "Ativar Notificações",
        default=True,
        description="Marque para ativar as notificações automáticas"
    )
    
    submeter = SubmitField("Salvar Configurações")

    def validate_emails(self, field) -> None:
        """
        Valida se os e-mails estão em formato correto.
        
        Args:
            field: Campo de emails do formulário
            
        Raises:
            ValidationError: Se os emails estiverem em formato inválido
        """
        if not field.data:
            raise ValidationError("Pelo menos um e-mail deve ser informado.")

        emails = [email.strip() for email in field.data.split("\n") if email.strip()]
        
        if not emails:
            raise ValidationError("Pelo menos um e-mail deve ser informado.")
        
        email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

        invalid_emails = []
        for email in emails:
            if not email_pattern.match(email):
                invalid_emails.append(email)
        
        if invalid_emails:
            raise ValidationError(f"E-mails inválidos: {', '.join(invalid_emails)}")
        
        # Verificar duplicados
        if len(emails) != len(set(emails)):
            raise ValidationError("Existem e-mails duplicados na lista.")
    
    def get_emails_list(self) -> List[str]:
        """
        Retorna lista de emails limpos.
        
        Returns:
            Lista de endereços de email formatados
        """
        if self.emails.data:
            return [email.strip() for email in self.emails.data.split("\n") if email.strip()]
        return []
    
    def set_emails_from_list(self, emails_list: List[str]) -> None:
        """
        Define emails a partir de uma lista.
        
        Args:
            emails_list: Lista de endereços de email
        """
        if emails_list:
            self.emails.data = "\n".join(emails_list)
    
    def get_prazos_dias(self) -> List[int]:
        """
        Obtém os prazos selecionados em formato numérico.
        
        Returns:
            Lista de prazos em dias (inteiros)
        """
        if hasattr(self, 'prazos') and self.prazos.data:
            return [int(prazo) for prazo in self.prazos.data]
        return [30, 15, 7, 3, 1]  # Valores padrão