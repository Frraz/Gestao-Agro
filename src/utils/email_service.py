#src/utils/email_service.py

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app
import datetime
import logging
from flask import render_template, current_app
import datetime


logger = logging.getLogger(__name__)

class EmailService:
    """Serviço para envio de e-mails"""
    
    def __init__(self):
        pass # As configurações são carregadas via current_app

    def send_email(self, destinatarios, assunto, corpo, html=False):
        """Envia e-mail para os destinatários."""
        print("MAIL_USERNAME:", current_app.config.get("MAIL_USERNAME"))
        print("MAIL_DEFAULT_SENDER:", current_app.config.get("MAIL_DEFAULT_SENDER"))
        if not destinatarios:
            logger.warning("Nenhum destinatário especificado para o e-mail.")
            return False
        
        try:
            smtp_server = current_app.config.get("MAIL_SERVER")
            port = current_app.config.get("MAIL_PORT")
            sender_email = current_app.config.get("MAIL_DEFAULT_SENDER")
            password = current_app.config.get("MAIL_PASSWORD")
            use_tls = current_app.config.get("MAIL_USE_TLS")

            if not all([smtp_server, port, sender_email, password]):
                logger.error("Configurações de e-mail incompletas. Verifique MAIL_SERVER, MAIL_PORT, MAIL_DEFAULT_SENDER e MAIL_PASSWORD.")
                return False
            
            message = MIMEMultipart("alternative")
            message["Subject"] = assunto
            message["From"] = sender_email
            message["To"] = ", ".join(destinatarios)
            
            if html:
                part = MIMEText(corpo, "html")
            else:
                part = MIMEText(corpo, "plain")
            message.attach(part)
            
            context = ssl.create_default_context()
            
            with smtplib.SMTP(smtp_server, port) as server:
                if use_tls:
                    server.starttls(context=context)
                server.login(current_app.config.get("MAIL_USERNAME"), password)
                server.sendmail(sender_email, destinatarios, message.as_string())
            
            logger.info(f"E-mail \'{assunto}\' enviado com sucesso para {len(destinatarios)} destinatário(s).")
            return True
        except Exception as e:
            logger.error(f"Erro ao enviar e-mail \'{assunto}\': {str(e)}")
            return False
    def enviar_email_teste(self, destinatarios):
        """Envia um e-mail de teste para verificar a configuração."""
        assunto = "Teste de Notificação - Sistema de Gestão Agrícola"
        data_hora_atual = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        corpo_html = f"""
        <html lang="pt">
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #f8f9fa; padding: 15px; border-bottom: 3px solid #dee2e6; }}
                .content {{ padding: 20px 0; }}
                .footer {{ font-size: 12px; color: #6c757d; padding-top: 20px; border-top: 1px solid #dee2e6; }}
                .alert-success {{ background-color: #d4edda; border: 1px solid #c3e6cb; padding: 15px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Teste de Notificação</h2>
                </div>
                <div class="content">
                    <div class="alert-success">
                        <h3>Teste realizado com sucesso!</h3>
                        <p>Este é um e-mail de teste do Sistema de Gestão Agrícola.</p>
                    </div>
                    
                    <p>Se você recebeu este e-mail, significa que a configuração de notificações está funcionando corretamente.</p>
                    <p>Você receberá notificações automáticas quando documentos estiverem próximos do vencimento.</p>
                </div>
                <div class="footer">
                    <p>Esta é uma mensagem automática do Sistema de Gestão Agrícola.</p>
                    <p>Não responda a este e-mail.</p>
                    <p>Data e hora do teste: {data_hora_atual}</p>
                </div>
            </div>
        </body>
        </html>
        """
        return self.send_email(destinatarios, assunto, corpo_html, html=True)

from flask import render_template, current_app
import datetime

def formatar_email_notificacao(documento, dias_restantes, responsavel=None, link_documento=None):
    """
    Formata o conteúdo do e-mail de notificação de vencimento.

    Args:
        documento: Objeto do modelo Documento
        dias_restantes: Número de dias restantes para o vencimento
        responsavel: Nome do responsável (opcional)
        link_documento: Link para o documento (opcional)

    Returns:
        Tupla com (assunto, corpo_html) do e-mail
    """
    # Determina a classe de alerta com base nos dias restantes
    if dias_restantes <= 3:
        classe_alerta = "danger"
        nivel_urgencia = "URGENTE"
    elif dias_restantes <= 7:
        classe_alerta = "warning"
        nivel_urgencia = "ATENÇÃO"
    else:
        classe_alerta = "info"
        nivel_urgencia = "AVISO"

    # Informações da entidade relacionada
    tipo_entidade = "Fazenda/Área" if documento.tipo_entidade.value == "Fazenda/Área" else "Pessoa"
    nome_entidade = documento.nome_entidade

    contexto = {
        "responsavel": responsavel,
        "nome_documento": documento.nome,
        "tipo_documento": documento.tipo.value,
        "data_emissao": documento.data_emissao.strftime('%d/%m/%Y'),
        "data_vencimento": documento.data_vencimento.strftime('%d/%m/%Y'),
        "tipo_entidade": tipo_entidade,
        "nome_entidade": nome_entidade,
        "dias_restantes": dias_restantes,
        "nivel_urgencia": nivel_urgencia,
        "classe_alerta": classe_alerta,
        "link_documento": link_documento,
        "ano_atual": datetime.datetime.now().year
    }

    # Garante contexto de app
    try:
        corpo_html = render_template("email/notificacao_vencimento.html", **contexto)
    except RuntimeError:
        with current_app.app_context():
            corpo_html = render_template("email/notificacao_vencimento.html", **contexto)

    assunto = f"{nivel_urgencia}: Documento '{documento.nome}' vence em {dias_restantes} dias"
    return assunto, corpo_html

def verificar_documentos_vencendo():
    """
    Verifica documentos próximos do vencimento e retorna lista agrupada por prazo.
    
    Returns:
        Dicionário com documentos agrupados por prazo de vencimento
    """
    from src.models.documento import Documento
    
    hoje = datetime.date.today()
    documentos_por_prazo = {}
    
    # Buscar todos os documentos com data de vencimento
    documentos = Documento.query.filter(Documento.data_vencimento.isnot(None)).all()
    
    for documento in documentos:
        if not documento.data_vencimento:
            continue
            
        dias_restantes = (documento.data_vencimento - hoje).days
        
        # Verificar se o documento está dentro de algum prazo de notificação
        for prazo in documento.prazos_notificacao:
            if dias_restantes == prazo:
                if prazo not in documentos_por_prazo:
                    documentos_por_prazo[prazo] = []
                documentos_por_prazo[prazo].append(documento)
    
    return documentos_por_prazo

email_service = EmailService()

def enviar_email_teste(destinatarios):
    return email_service.enviar_email_teste(destinatarios)