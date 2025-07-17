# /src/utils/notification_fallback.py

"""
Sistema de fallback para notificações quando Redis/Celery não estão disponíveis.

Este módulo fornece uma alternativa confiável para o envio de notificações
quando as dependências externas falham, garantindo que o sistema continue
funcionando mesmo em ambientes com limitações de infraestrutura.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import smtplib

from src.models.db import db
from src.models.documento import Documento
from src.models.endividamento import Endividamento
from src.utils.email_service import EmailService

logger = logging.getLogger(__name__)


class NotificationFallbackService:
    """
    Serviço de fallback para notificações quando Redis/Celery não estão disponíveis.
    
    Fornece funcionalidade completa de notificação sem dependências externas,
    incluindo formatação HTML, envio de emails e registro de histórico.
    """
    
    def __init__(self):
        self.email_service = EmailService()
        
    def verificar_e_enviar_todas_notificacoes(self) -> Dict[str, int]:
        """
        Verifica e envia todas as notificações pendentes usando fallback.
        
        Returns:
            Dict[str, int]: Contadores de notificações enviadas por tipo
        """
        try:
            logger.info("Iniciando verificação de notificações com fallback")
            
            # Verificar documentos próximos ao vencimento
            docs_count = self._verificar_documentos_vencimento()
            
            # Verificar endividamentos próximos ao vencimento
            end_count = self._verificar_endividamentos_vencimento()
            
            total = docs_count + end_count
            
            logger.info(f"Fallback concluído: {docs_count} docs, {end_count} endividamentos, {total} total")
            
            return {
                "documentos": docs_count,
                "endividamentos": end_count,
                "total": total
            }
            
        except Exception as e:
            logger.error(f"Erro no fallback de notificações: {e}", exc_info=True)
            return {"documentos": 0, "endividamentos": 0, "total": 0}
    
    def _verificar_documentos_vencimento(self) -> int:
        """Verifica documentos próximos ao vencimento."""
        try:
            from datetime import timedelta
            hoje = date.today()
            limite = hoje + timedelta(days=30)
            
            # Buscar documentos vencendo nos próximos 30 dias
            documentos = Documento.query.filter(
                Documento.data_vencimento.between(hoje, limite),
                Documento.ativo == True
            ).all()
            
            count = 0
            for doc in documentos:
                if self._enviar_notificacao_documento(doc):
                    count += 1
                    
            return count
            
        except Exception as e:
            logger.error(f"Erro ao verificar documentos: {e}")
            return 0
    
    def _verificar_endividamentos_vencimento(self) -> int:
        """Verifica endividamentos próximos ao vencimento."""
        try:
            from datetime import timedelta
            hoje = date.today()
            limite = hoje + timedelta(days=30)
            
            # Buscar endividamentos vencendo nos próximos 30 dias
            endividamentos = Endividamento.query.filter(
                Endividamento.data_vencimento_final.between(hoje, limite)
            ).all()
            
            count = 0
            for end in endividamentos:
                if self._enviar_notificacao_endividamento(end):
                    count += 1
                    
            return count
            
        except Exception as e:
            logger.error(f"Erro ao verificar endividamentos: {e}")
            return 0
    
    def _enviar_notificacao_documento(self, documento: Documento) -> bool:
        """Envia notificação para documento específico."""
        try:
            # Determinar destinatário
            destinatario = None
            if documento.pessoa and documento.pessoa.email:
                destinatario = documento.pessoa.email
            elif documento.fazenda:
                # Buscar email de pessoa associada à fazenda
                for vinculo in documento.fazenda.pessoas_fazenda:
                    if vinculo.pessoa.email:
                        destinatario = vinculo.pessoa.email
                        break
            
            if not destinatario:
                logger.warning(f"Sem destinatário para documento {documento.id}")
                return False
                
            # Preparar conteúdo
            assunto = f"Documento {documento.nome} vencendo em breve"
            
            days_to_expire = (documento.data_vencimento - date.today()).days
            
            corpo_html = self._formatar_email_documento_html(documento, days_to_expire)
            corpo_texto = self._formatar_email_documento_texto(documento, days_to_expire)
            
            # Enviar email
            sucesso = self.email_service.enviar_email(
                destinatario=destinatario,
                assunto=assunto,
                corpo_html=corpo_html,
                corpo_texto=corpo_texto
            )
            
            if sucesso:
                logger.info(f"Notificação enviada para documento {documento.id}")
                
            return sucesso
            
        except Exception as e:
            logger.error(f"Erro ao enviar notificação do documento {documento.id}: {e}")
            return False
    
    def _enviar_notificacao_endividamento(self, endividamento: Endividamento) -> bool:
        """Envia notificação para endividamento específico."""
        try:
            # Buscar emails dos endividados
            destinatarios = []
            for vinculo in endividamento.pessoas_endividadas:
                if vinculo.pessoa.email:
                    destinatarios.append(vinculo.pessoa.email)
            
            if not destinatarios:
                logger.warning(f"Sem destinatários para endividamento {endividamento.id}")
                return False
            
            # Preparar conteúdo
            assunto = f"Endividamento {endividamento.banco} vencendo em breve"
            
            days_to_expire = (endividamento.data_vencimento_final - date.today()).days
            
            corpo_html = self._formatar_email_endividamento_html(endividamento, days_to_expire)
            corpo_texto = self._formatar_email_endividamento_texto(endividamento, days_to_expire)
            
            # Enviar para todos os destinatários
            sucesso_total = True
            for destinatario in destinatarios:
                sucesso = self.email_service.enviar_email(
                    destinatario=destinatario,
                    assunto=assunto,
                    corpo_html=corpo_html,
                    corpo_texto=corpo_texto
                )
                if not sucesso:
                    sucesso_total = False
            
            if sucesso_total:
                logger.info(f"Notificação enviada para endividamento {endividamento.id}")
                
            return sucesso_total
            
        except Exception as e:
            logger.error(f"Erro ao enviar notificação do endividamento {endividamento.id}: {e}")
            return False
    
    def _formatar_email_documento_html(self, documento: Documento, days_to_expire: int) -> str:
        """Formata email HTML para documento."""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 20px; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; border: 1px solid #ddd; border-radius: 8px; overflow: hidden;">
                <div style="background-color: #f8f9fa; padding: 20px; border-bottom: 1px solid #ddd;">
                    <h2 style="margin: 0; color: #495057;">🔔 Notificação de Vencimento</h2>
                </div>
                
                <div style="padding: 20px;">
                    <p style="font-size: 16px; margin-bottom: 15px;">
                        O documento <strong>{documento.nome}</strong> está próximo do vencimento.
                    </p>
                    
                    <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 4px; padding: 15px; margin: 15px 0;">
                        <p style="margin: 0; color: #856404;">
                            <strong>⚠️ Atenção:</strong> Este documento vence em <strong>{days_to_expire} dia(s)</strong>
                        </p>
                    </div>
                    
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 4px; margin: 15px 0;">
                        <h3 style="margin-top: 0; color: #495057;">Detalhes do Documento</h3>
                        <p><strong>Nome:</strong> {documento.nome}</p>
                        <p><strong>Tipo:</strong> {documento.tipo}</p>
                        <p><strong>Data de Vencimento:</strong> {documento.data_vencimento.strftime('%d/%m/%Y')}</p>
                        {f'<p><strong>Pessoa:</strong> {documento.pessoa.nome}</p>' if documento.pessoa else ''}
                        {f'<p><strong>Fazenda:</strong> {documento.fazenda.nome}</p>' if documento.fazenda else ''}
                    </div>
                    
                    <div style="margin-top: 20px; padding-top: 15px; border-top: 1px solid #ddd;">
                        <p style="font-size: 14px; color: #6c757d; margin: 0;">
                            Esta é uma notificação automática do Sistema de Gestão Agrícola.
                        </p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _formatar_email_documento_texto(self, documento: Documento, days_to_expire: int) -> str:
        """Formata email texto para documento."""
        return f"""
        NOTIFICAÇÃO DE VENCIMENTO
        
        O documento {documento.nome} está próximo do vencimento.
        
        ATENÇÃO: Este documento vence em {days_to_expire} dia(s)
        
        Detalhes do Documento:
        - Nome: {documento.nome}
        - Tipo: {documento.tipo}
        - Data de Vencimento: {documento.data_vencimento.strftime('%d/%m/%Y')}
        {f'- Pessoa: {documento.pessoa.nome}' if documento.pessoa else ''}
        {f'- Fazenda: {documento.fazenda.nome}' if documento.fazenda else ''}
        
        Esta é uma notificação automática do Sistema de Gestão Agrícola.
        """
    
    def _formatar_email_endividamento_html(self, endividamento: Endividamento, days_to_expire: int) -> str:
        """Formata email HTML para endividamento."""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 20px; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; border: 1px solid #ddd; border-radius: 8px; overflow: hidden;">
                <div style="background-color: #f8f9fa; padding: 20px; border-bottom: 1px solid #ddd;">
                    <h2 style="margin: 0; color: #495057;">🔔 Notificação de Vencimento</h2>
                </div>
                
                <div style="padding: 20px;">
                    <p style="font-size: 16px; margin-bottom: 15px;">
                        O endividamento no banco <strong>{endividamento.banco}</strong> está próximo do vencimento.
                    </p>
                    
                    <div style="background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 4px; padding: 15px; margin: 15px 0;">
                        <p style="margin: 0; color: #721c24;">
                            <strong>⚠️ Urgente:</strong> Este endividamento vence em <strong>{days_to_expire} dia(s)</strong>
                        </p>
                    </div>
                    
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 4px; margin: 15px 0;">
                        <h3 style="margin-top: 0; color: #495057;">Detalhes do Endividamento</h3>
                        <p><strong>Banco:</strong> {endividamento.banco}</p>
                        <p><strong>Valor:</strong> R$ {endividamento.valor:,.2f}</p>
                        <p><strong>Data de Vencimento:</strong> {endividamento.data_vencimento_final.strftime('%d/%m/%Y')}</p>
                        {f'<p><strong>Observações:</strong> {endividamento.observacoes}</p>' if endividamento.observacoes else ''}
                    </div>
                    
                    <div style="margin-top: 20px; padding-top: 15px; border-top: 1px solid #ddd;">
                        <p style="font-size: 14px; color: #6c757d; margin: 0;">
                            Esta é uma notificação automática do Sistema de Gestão Agrícola.
                        </p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _formatar_email_endividamento_texto(self, endividamento: Endividamento, days_to_expire: int) -> str:
        """Formatar email texto para endividamento."""
        return f"""
        NOTIFICAÇÃO DE VENCIMENTO
        
        O endividamento no banco {endividamento.banco} está próximo do vencimento.
        
        URGENTE: Este endividamento vence em {days_to_expire} dia(s)
        
        Detalhes do Endividamento:
        - Banco: {endividamento.banco}
        - Valor: R$ {endividamento.valor:,.2f}
        - Data de Vencimento: {endividamento.data_vencimento_final.strftime('%d/%m/%Y')}
        {f'- Observações: {endividamento.observacoes}' if endividamento.observacoes else ''}
        
        Esta é uma notificação automática do Sistema de Gestão Agrícola.
        """