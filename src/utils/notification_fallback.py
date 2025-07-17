# /src/utils/notification_fallback.py

"""
Sistema de notificações de fallback que funciona sem Redis/Celery
Usado quando o sistema distribuído não está disponível
"""

import datetime
import logging
from typing import List

from src.models.db import db
from src.models.documento import Documento
from src.utils.email_service import EmailService

logger = logging.getLogger(__name__)


class NotificationFallbackService:
    """
    Sistema de notificações que funciona sem Redis/Celery
    """
    
    def __init__(self):
        self.email_service = EmailService()
    
    def check_and_send_notifications(self) -> dict:
        """
        Verifica e envia notificações sem depender de Redis/Celery
        Retorna estatísticas do processamento
        """
        result = {
            'documents_checked': 0,
            'notifications_sent': 0,
            'errors': [],
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        try:
            today = datetime.date.today()
            
            # Buscar documentos com data de vencimento definida
            documents = Documento.query.filter(
                Documento.data_vencimento.isnot(None),
                Documento.data_vencimento >= today
            ).all()
            
            result['documents_checked'] = len(documents)
            
            for doc in documents:
                try:
                    days_until_expiry = (doc.data_vencimento - today).days
                    
                    # Verificar se precisa notificar
                    if self._should_notify(doc, days_until_expiry):
                        if self._send_notification(doc, days_until_expiry):
                            result['notifications_sent'] += 1
                            logger.info(f"Notificação enviada para documento {doc.id}: {doc.nome}")
                        else:
                            result['errors'].append(f"Falha ao enviar notificação para documento {doc.id}")
                            
                except Exception as e:
                    error_msg = f"Erro ao processar documento {doc.id}: {str(e)}"
                    result['errors'].append(error_msg)
                    logger.error(error_msg)
                    
        except Exception as e:
            error_msg = f"Erro geral no processamento de notificações: {str(e)}"
            result['errors'].append(error_msg)
            logger.error(error_msg)
            
        return result
    
    def _should_notify(self, document: Documento, days_until_expiry: int) -> bool:
        """
        Determina se deve enviar notificação para um documento
        """
        # Prazos padrão de notificação
        default_notification_days = [90, 60, 30, 15, 7, 3, 1]
        
        # Tentar obter prazos específicos do documento
        notification_days = default_notification_days
        
        if hasattr(document, 'prazos_notificacao') and document.prazos_notificacao:
            try:
                if isinstance(document.prazos_notificacao, str):
                    import json
                    notification_days = json.loads(document.prazos_notificacao)
                elif isinstance(document.prazos_notificacao, list):
                    notification_days = document.prazos_notificacao
            except:
                pass  # Usa padrão em caso de erro
        
        return days_until_expiry in notification_days
    
    def _send_notification(self, document: Documento, days_until_expiry: int) -> bool:
        """
        Envia notificação por e-mail para um documento
        """
        try:
            # Determinar destinatários
            recipients = self._get_recipients(document)
            
            if not recipients:
                logger.warning(f"Nenhum destinatário encontrado para documento {document.id}")
                return False
            
            # Preparar conteúdo do e-mail
            subject = f"⚠️ Documento vencendo em {days_until_expiry} dias: {document.nome}"
            
            body = self._format_email_body(document, days_until_expiry)
            
            # Enviar e-mail
            return self.email_service.send_email(recipients, subject, body, html=True)
            
        except Exception as e:
            logger.error(f"Erro ao enviar notificação para documento {document.id}: {str(e)}")
            return False
    
    def _get_recipients(self, document: Documento) -> List[str]:
        """
        Obtém lista de destinatários para a notificação
        """
        recipients = []
        
        # Emails específicos do documento
        if hasattr(document, 'emails_notificacao') and document.emails_notificacao:
            if isinstance(document.emails_notificacao, str):
                # Se for string, assumir que são emails separados por vírgula
                recipients.extend([email.strip() for email in document.emails_notificacao.split(',')])
            elif isinstance(document.emails_notificacao, list):
                recipients.extend(document.emails_notificacao)
        
        # Se o documento está vinculado a pessoas, incluir emails das pessoas
        if hasattr(document, 'pessoa') and document.pessoa and document.pessoa.email:
            recipients.append(document.pessoa.email)
        
        # Se o documento está vinculado a fazenda e a fazenda tem pessoas associadas
        if hasattr(document, 'fazenda') and document.fazenda:
            for pessoa in document.fazenda.pessoas:
                if pessoa.email:
                    recipients.append(pessoa.email)
        
        # Remover duplicatas e emails vazios
        recipients = list(set([email for email in recipients if email and '@' in email]))
        
        return recipients
    
    def _format_email_body(self, document: Documento, days_until_expiry: int) -> str:
        """
        Formata o corpo do e-mail de notificação
        """
        urgency_level = "🔴 URGENTE" if days_until_expiry <= 3 else "🟡 ATENÇÃO" if days_until_expiry <= 7 else "🟢 AVISO"
        
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                <h2 style="color: #2c3e50; text-align: center;">{urgency_level} - Documento Vencendo</h2>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #495057;">Detalhes do Documento:</h3>
                    <p><strong>Nome:</strong> {document.nome}</p>
                    <p><strong>Tipo:</strong> {document.tipo.value if hasattr(document.tipo, 'value') else str(document.tipo)}</p>
                    <p><strong>Data de Vencimento:</strong> {document.data_vencimento.strftime('%d/%m/%Y')}</p>
                    <p><strong>Dias até o vencimento:</strong> <span style="color: {'red' if days_until_expiry <= 7 else 'orange'}; font-weight: bold;">{days_until_expiry} dias</span></p>
                </div>
                
                {self._get_entity_info_html(document)}
                
                <div style="background-color: #e7f3ff; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h4 style="margin-top: 0; color: #0056b3;">📋 Ação Necessária:</h4>
                    <p>Este documento precisa ser renovado ou atualizado antes da data de vencimento para evitar problemas legais ou operacionais.</p>
                </div>
                
                <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;">
                    <p style="color: #6c757d; font-size: 12px;">
                        Sistema de Gestão Agrícola<br>
                        Notificação automática enviada em {datetime.datetime.now().strftime('%d/%m/%Y às %H:%M')}
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return body
    
    def _get_entity_info_html(self, document: Documento) -> str:
        """
        Gera HTML com informações da entidade vinculada ao documento
        """
        html = ""
        
        if hasattr(document, 'fazenda') and document.fazenda:
            html += f"""
            <div style="background-color: #f0f8f0; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h4 style="margin-top: 0; color: #155724;">🏞️ Fazenda Vinculada:</h4>
                <p><strong>Nome:</strong> {document.fazenda.nome}</p>
                <p><strong>Matrícula:</strong> {document.fazenda.matricula}</p>
                <p><strong>Localização:</strong> {document.fazenda.municipio}, {document.fazenda.estado}</p>
            </div>
            """
        
        if hasattr(document, 'pessoa') and document.pessoa:
            html += f"""
            <div style="background-color: #f0f4f8; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h4 style="margin-top: 0; color: #1e3a8a;">👤 Pessoa Responsável:</h4>
                <p><strong>Nome:</strong> {document.pessoa.nome}</p>
                <p><strong>CPF/CNPJ:</strong> {document.pessoa.cpf_cnpj}</p>
                {f'<p><strong>Telefone:</strong> {document.pessoa.telefone}</p>' if document.pessoa.telefone else ''}
            </div>
            """
        
        return html


# Instância global para uso em outros módulos
notification_fallback_service = NotificationFallbackService()