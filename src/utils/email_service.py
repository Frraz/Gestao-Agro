# src/utils/email_service.py

"""
Serviço para envio de e-mails com suporte a templates e notificações
"""

import datetime
import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional, Tuple, Dict, Any, Union
from time import sleep

from flask import current_app, render_template

logger = logging.getLogger(__name__)


class EmailService:
    """Serviço para envio de e-mails"""

    def __init__(self):
        self._smtp_connection = None
        self._connection_count = 0
        self._max_emails_per_connection = 20

    def send_email(self, destinatarios: List[str], assunto: str, corpo: str, html: bool = False) -> bool:
        """Envia e-mail para os destinatários."""
        if not destinatarios:
            logger.warning("Nenhum destinatário especificado para o e-mail.")
            return False

        try:
            smtp_server = current_app.config.get("MAIL_SERVER")
            port = current_app.config.get("MAIL_PORT")
            sender_email = current_app.config.get("MAIL_DEFAULT_SENDER")
            username = current_app.config.get("MAIL_USERNAME", sender_email)
            password = current_app.config.get("MAIL_PASSWORD")
            use_tls = current_app.config.get("MAIL_USE_TLS", True)

            # Validar configurações
            if not all([smtp_server, port, sender_email, password]):
                logger.error(
                    "Configurações de e-mail incompletas. Verifique MAIL_SERVER, MAIL_PORT, "
                    "MAIL_DEFAULT_SENDER e MAIL_PASSWORD."
                )
                return False

            # Criar mensagem
            message = MIMEMultipart("alternative")
            message["Subject"] = assunto
            message["From"] = sender_email
            message["To"] = ", ".join(destinatarios)
            message["Date"] = datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")

            # Adicionar corpo
            if html:
                part = MIMEText(corpo, "html", "utf-8")
            else:
                part = MIMEText(corpo, "plain", "utf-8")
            message.attach(part)

            # Configurar conexão segura
            context = ssl.create_default_context()
            
            # Usar conexão existente ou criar nova
            should_close = False
            if self._smtp_connection and self._connection_count < self._max_emails_per_connection:
                try:
                    # Verificar se a conexão ainda está ativa
                    self._smtp_connection.noop()
                    server = self._smtp_connection
                    logger.debug("Reutilizando conexão SMTP existente")
                except:
                    # Fechar conexão problemática
                    self._close_connection()
                    should_close = True
                    # Criar nova conexão
                    server = smtplib.SMTP(smtp_server, port, timeout=30)
                    if use_tls:
                        server.starttls(context=context)
                    server.login(username, password)
                    self._smtp_connection = server
                    self._connection_count = 0
                    logger.debug("Criada nova conexão SMTP")
            else:
                # Fechar conexão anterior se existir
                self._close_connection()
                should_close = True
                # Criar nova conexão
                server = smtplib.SMTP(smtp_server, port, timeout=30)
                if use_tls:
                    server.starttls(context=context)
                server.login(username, password)
                self._smtp_connection = server
                self._connection_count = 0
                logger.debug("Criada nova conexão SMTP")

            # Enviar e-mail
            server.sendmail(sender_email, destinatarios, message.as_string())
            self._connection_count += 1
            
            # Fechar conexão se necessário
            if should_close:
                self._close_connection()

            logger.info(
                f"E-mail '{assunto}' enviado com sucesso para {len(destinatarios)} destinatário(s)."
            )
            return True
        
        except smtplib.SMTPAuthenticationError:
            logger.error("Falha na autenticação SMTP. Verifique usuário e senha.")
            return False
        
        except smtplib.SMTPRecipientsRefused as e:
            logger.error(f"Destinatários recusados pelo servidor: {e.recipients}")
            return False
        
        except smtplib.SMTPException as e:
            logger.error(f"Erro SMTP ao enviar e-mail '{assunto}': {str(e)}")
            self._close_connection()  # Fechar conexão problemática
            return False
        
        except Exception as e:
            logger.error(f"Erro ao enviar e-mail '{assunto}': {str(e)}", exc_info=True)
            self._close_connection()  # Fechar conexão problemática
            return False

    def _close_connection(self):
        """Fecha a conexão SMTP se existir"""
        if self._smtp_connection:
            try:
                self._smtp_connection.quit()
            except:
                pass
            finally:
                self._smtp_connection = None
                self._connection_count = 0

    def enviar_email_teste(self, destinatarios: List[str]) -> bool:
        """Envia um e-mail de teste para verificar a configuração."""
        assunto = "Teste de Notificação - Sistema de Gestão Agrícola"
        data_hora_atual = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        corpo_html = f"""
        <html lang="pt">
        <head>
            <meta charset="UTF-8">
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
        
    def __del__(self):
        """Destrutor para garantir fechamento da conexão"""
        self._close_connection()


def formatar_email_notificacao(
    documento, dias_restantes: int, responsavel: Optional[str] = None, link_documento: Optional[str] = None
) -> Tuple[str, str]:
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
    if dias_restantes <= 0:
        classe_alerta = "danger"
        nivel_urgencia = "VENCIDO"
    elif dias_restantes <= 3:
        classe_alerta = "danger"
        nivel_urgencia = "URGENTE"
    elif dias_restantes <= 7:
        classe_alerta = "warning"
        nivel_urgencia = "ATENÇÃO"
    else:
        classe_alerta = "info"
        nivel_urgencia = "AVISO"

    # Informações da entidade relacionada - torna robusto para ausência de tipo_entidade
    tipo_entidade = "Pessoa"
    if hasattr(documento, "tipo_entidade") and getattr(documento, "tipo_entidade", None):
        tipo_entidade_val = getattr(documento.tipo_entidade, "value", documento.tipo_entidade)
        if tipo_entidade_val == "Fazenda/Área":
            tipo_entidade = "Fazenda/Área"
        else:
            tipo_entidade = str(tipo_entidade_val)
    nome_entidade = getattr(documento, "nome_entidade", "")

    # Preparar contexto para o template
    contexto = {
        "responsavel": responsavel or "Usuário",
        "nome_documento": getattr(documento, "nome", ""),
        "tipo_documento": getattr(getattr(documento, "tipo", None), "value", getattr(documento, "tipo", "")),
        "data_emissao": documento.data_emissao.strftime("%d/%m/%Y") if getattr(documento, "data_emissao", None) else "N/A",
        "data_vencimento": documento.data_vencimento.strftime("%d/%m/%Y") if getattr(documento, "data_vencimento", None) else "N/A",
        "tipo_entidade": tipo_entidade,
        "nome_entidade": nome_entidade,
        "dias_restantes": dias_restantes,
        "nivel_urgencia": nivel_urgencia,
        "classe_alerta": classe_alerta,
        "link_documento": link_documento,
        "ano_atual": datetime.datetime.now().year,
    }

    # Tentar renderizar com template, ou usar template fallback embutido
    try:
        try:
            corpo_html = render_template("email/notificacao_vencimento.html", **contexto)
        except RuntimeError:
            with current_app.app_context():
                corpo_html = render_template("email/notificacao_vencimento.html", **contexto)
    except Exception as e:
        # Fallback para template embutido em caso de erro
        logger.warning(f"Erro ao renderizar template de email: {e}, usando fallback")
        corpo_html = f"""
        <!DOCTYPE html>
        <html lang="pt-br">
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: {{'#dc3545' if classe_alerta == 'danger' else '#ffc107' if classe_alerta == 'warning' else '#17a2b8'}}; 
                          color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .info-box {{ background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 15px; margin: 20px 0; border-radius: 4px; }}
                .footer {{ font-size: 12px; color: #6c757d; margin-top: 30px; padding-top: 10px; border-top: 1px solid #dee2e6; }}
                .btn {{ display: inline-block; background-color: #007bff; color: white; padding: 10px 15px; 
                      text-decoration: none; border-radius: 4px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{nivel_urgencia}</h1>
                    <h2>Documento próximo do vencimento</h2>
                </div>
                <div class="content">
                    <p>Olá {contexto['responsavel']},</p>
                    
                    <p>O documento <strong>{contexto['nome_documento']}</strong> 
                    {{'está vencido' if dias_restantes <= 0 else f'vence em {dias_restantes} dias'}}.</p>
                    
                    <div class="info-box">
                        <p><strong>Documento:</strong> {contexto['nome_documento']}<br>
                        <strong>Tipo:</strong> {contexto['tipo_documento']}<br>
                        <strong>{contexto['tipo_entidade']}:</strong> {contexto['nome_entidade']}<br>
                        <strong>Data de Emissão:</strong> {contexto['data_emissao']}<br>
                        <strong>Data de Vencimento:</strong> {contexto['data_vencimento']}</p>
                    </div>
                    
                    <p>Por favor, tome as providências necessárias para regularização deste documento.</p>
                    
                    {f'<a href="{link_documento}" class="btn">Visualizar Documento</a>' if link_documento else ''}
                </div>
                <div class="footer">
                    <p>Esta é uma mensagem automática do Sistema de Gestão Agrícola.</p>
                    <p>© {datetime.datetime.now().year} - Sistema de Gestão Agrícola</p>
                </div>
            </div>
        </body>
        </html>
        """

    # Formatar assunto de acordo com a situação
    if dias_restantes <= 0:
        assunto = f"{nivel_urgencia}: Documento '{contexto['nome_documento']}' VENCIDO"
    else:
        assunto = f"{nivel_urgencia}: Documento '{contexto['nome_documento']}' vence em {dias_restantes} dias"
        
    return assunto, corpo_html


def verificar_documentos_vencendo() -> Dict[int, List]:
    """
    Verifica documentos próximos do vencimento e retorna lista agrupada por prazo.

    Returns:
        Dicionário com documentos agrupados por prazo de vencimento
    """
    from src.models.documento import Documento

    hoje = datetime.date.today()
    documentos_por_prazo = {}

    try:
        # Buscar todos os documentos com data de vencimento
        documentos = Documento.query.filter(Documento.data_vencimento.isnot(None)).all()

        for documento in documentos:
            if not documento.data_vencimento:
                continue

            dias_restantes = (documento.data_vencimento - hoje).days

            # Verificar se o documento está dentro de algum prazo de notificação
            # Se não tiver prazos configurados, usa padrão de 1, 7, 30 dias
            prazos = getattr(documento, "prazos_notificacao", [1, 7, 30, 60, 90])
            
            for prazo in prazos:
                if dias_restantes == prazo:
                    if prazo not in documentos_por_prazo:
                        documentos_por_prazo[prazo] = []
                    documentos_por_prazo[prazo].append(documento)
            
            # Adicionar documentos vencidos (dias_restantes <= 0) em uma categoria especial
            if dias_restantes <= 0:
                if 0 not in documentos_por_prazo:
                    documentos_por_prazo[0] = []
                documentos_por_prazo[0].append(documento)
    
    except Exception as e:
        logger.error(f"Erro ao verificar documentos vencendo: {e}", exc_info=True)
    
    return documentos_por_prazo


def enviar_notificacao_lote(emails: List[Dict], batch_size: int = 10) -> Dict:
    """
    Envia um lote de emails de notificação
    
    Args:
        emails: Lista de dicionários com dados de emails
        batch_size: Tamanho de cada lote de envio
        
    Returns:
        Estatísticas de envio
    """
    stats = {"total": len(emails), "enviados": 0, "falhas": 0}
    
    # Enviar em lotes para evitar sobrecarga
    for i in range(0, len(emails), batch_size):
        lote = emails[i:i+batch_size]
        
        for email_data in lote:
            try:
                destinatarios = email_data.get("destinatarios", [])
                assunto = email_data.get("assunto", "")
                corpo = email_data.get("corpo", "")
                html = email_data.get("html", True)
                
                sucesso = email_service.send_email(destinatarios, assunto, corpo, html)
                
                if sucesso:
                    stats["enviados"] += 1
                else:
                    stats["falhas"] += 1
            except Exception as e:
                logger.error(f"Erro ao enviar email do lote: {e}")
                stats["falhas"] += 1
        
        # Pequena pausa entre lotes
        if i + batch_size < len(emails):
            sleep(1)
    
    return stats


# Instância global do serviço
email_service = EmailService()


def enviar_email_teste(destinatarios: List[str]) -> bool:
    """Função auxiliar para enviar email de teste"""
    return email_service.enviar_email_teste(destinatarios)