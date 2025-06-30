# /src/utils/notificacao_documentos_service.py

import datetime
import logging

from src.models.documento import Documento
from src.utils.email_service import email_service, formatar_email_notificacao

logger = logging.getLogger(__name__)


class NotificacaoDocumentoService:
    """
    Serviço para gerenciar notificações automáticas de vencimento de documentos.
    """

    def __init__(self):
        self.email_service = email_service

    def verificar_e_enviar_notificacoes(self):
        """
        Verifica todos os documentos com prazos de notificação e envia e-mails quando necessário.
        Retorna o número total de notificações enviadas.
        """
        hoje = datetime.date.today()
        total_enviadas = 0

        # Buscar todos os documentos com data de vencimento e prazos de notificação configurados
        documentos = Documento.query.filter(Documento.data_vencimento.isnot(None)).all()

        for documento in documentos:
            # Garante que o documento possui prazos para notificação
            if (
                not hasattr(documento, "prazos_notificacao")
                or not documento.prazos_notificacao
            ):
                continue

            # Calcula dias restantes para o vencimento
            dias_restantes = (documento.data_vencimento - hoje).days

            # Para cada prazo de notificação configurado, verifica se deve enviar
            for prazo in documento.prazos_notificacao:
                if dias_restantes == prazo:
                    try:
                        # Determina destinatários
                        destinatarios = []
                        responsavel_nome = None
                        responsavel = getattr(documento, "responsavel", None)
                        if responsavel and getattr(responsavel, "email", None):
                            destinatarios.append(responsavel.email)
                            responsavel_nome = (
                                getattr(responsavel, "nome", None) or responsavel.email
                            )
                        elif (
                            hasattr(documento, "emails_notificacao")
                            and documento.emails_notificacao
                        ):
                            # Campo alternativo (exemplo: lista de e-mails)
                            destinatarios = documento.emails_notificacao

                        if not destinatarios:
                            logger.warning(
                                f"Documento {documento.id} sem destinatário para notificação"
                            )
                            continue

                        # Monta e envia notificação
                        assunto, corpo_html = formatar_email_notificacao(
                            documento,
                            dias_restantes,
                            responsavel=responsavel_nome,
                            link_documento=getattr(
                                documento, "link_visualizacao", None
                            ),
                        )
                        enviado = self.email_service.send_email(
                            destinatarios, assunto, corpo_html, html=True
                        )
                        if enviado:
                            logger.info(
                                f"Notificação de vencimento enviada para documento {documento.id}: {destinatarios}"
                            )
                            total_enviadas += 1
                        else:
                            logger.error(
                                f"Falha ao enviar notificação de documento {documento.id} para {destinatarios}"
                            )

                    except Exception as e:
                        logger.error(
                            f"Erro ao enviar notificação de documento {documento.id}: {e}"
                        )
        return total_enviadas


# Instância pronta para uso em tasks agendadas
notificacao_documento_service = NotificacaoDocumentoService()


def processar_notificacoes_documentos():
    """
    Função utilitária para ser usada em agendadores (Celery, cron, etc).
    """
    return notificacao_documento_service.verificar_e_enviar_notificacoes()
