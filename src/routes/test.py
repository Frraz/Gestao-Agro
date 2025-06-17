from flask import Blueprint
import datetime
from src.utils.email_service import formatar_email_notificacao, EmailService

test_bp = Blueprint('test', __name__, url_prefix='/test')

@test_bp.route('/enviar-email-real')
def enviar_email_real():
    class DummyDoc:
        nome = "Licença Ambiental"
        tipo = type("Tipo", (), {"value": "Certidão"})
        data_emissao = datetime.datetime(2024, 1, 1)
        data_vencimento = datetime.datetime(2024, 12, 31)
        tipo_entidade = type("TipoEntidade", (), {"value": "Fazenda/Área"})
        nome_entidade = "Fazenda Santa Luzia"
    doc = DummyDoc()
    dias_restantes = 5
    assunto, corpo_html = formatar_email_notificacao(
        doc, dias_restantes, responsavel="Fulano", link_documento="https://meusistema.com/doc/123"
    )
    enviado = EmailService().send_email(
        ["warley.ferraz.wf@gmail.com"],
        assunto,
        corpo_html,
        html=True
    )
    if enviado:
        return "E-mail enviado com sucesso para warley.ferraz.wf@gmail.com!"
    else:
        return "Falha ao enviar e-mail."