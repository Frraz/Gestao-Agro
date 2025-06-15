# Formulário para Notificações de Endividamento
from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, TextAreaField
from wtforms.validators import DataRequired, Email, Length
from wtforms.widgets import TextArea

class NotificacaoEndividamentoForm(FlaskForm):
    """Formulário para configuração de notificações de endividamento"""
    emails = TextAreaField('E-mails para Notificação', 
                          validators=[DataRequired(), Length(max=2000)],
                          description='Digite um e-mail por linha. As notificações serão enviadas nos seguintes intervalos: 6 meses, 3 meses, 30 dias, 15 dias, 7 dias, 3 dias e 1 dia antes do vencimento.')
    ativo = BooleanField('Ativo', default=True, description='Marque para ativar as notificações automáticas')
    
    def validate_emails(self, field):
        """Valida se os e-mails estão em formato correto"""
        from wtforms.validators import ValidationError
        import re
        
        if not field.data:
            return
            
        emails = [email.strip() for email in field.data.split('\n') if email.strip()]
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        
        for email in emails:
            if not email_pattern.match(email):
                raise ValidationError(f'E-mail inválido: {email}')

