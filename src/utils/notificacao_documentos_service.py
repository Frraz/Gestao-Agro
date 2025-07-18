# /src/utils/notificacao_documentos_service.py

# Serviço de Notificações para Documentos
import datetime
import logging
import json
from collections import defaultdict

from src.models.db import db
from src.models.documento import Documento
from src.utils.email_service import email_service, formatar_email_notificacao

logger = logging.getLogger(__name__)


class NotificacaoDocumentoService:
    """
    Serviço para gerenciar notificações automáticas de vencimento de documentos.
    """
    
    # Prazos padrão de notificação em dias
    PRAZOS_PADRAO = [90, 60, 30, 15, 7, 3, 1]

    def __init__(self):
        self.email_service = email_service
        self._notificacoes_enviadas_hoje = defaultdict(set)

    def verificar_e_enviar_notificacoes(self):
        """
        Verifica todos os documentos com prazos de notificação e envia e-mails quando necessário.
        Retorna o número total de notificações enviadas.
        """
        hoje = datetime.date.today()
        total_enviadas = 0

        try:
            # Buscar todos os documentos com data de vencimento
            documentos = Documento.query.filter(
                Documento.data_vencimento.isnot(None),
                Documento.data_vencimento >= hoje  # Apenas documentos ainda não vencidos
            ).all()

            logger.info(f"Verificando {len(documentos)} documentos para notificações")

            for documento in documentos:
                # Calcula dias restantes para o vencimento
                dias_restantes = (documento.data_vencimento - hoje).days
                
                # Determina os prazos de notificação para este documento
                prazos = self._obter_prazos_notificacao(documento)
                
                # Verifica se deve enviar notificação hoje
                if dias_restantes in prazos:
                    # Evita enviar múltiplas notificações para o mesmo documento no mesmo dia
                    chave_notificacao = f"{documento.id}_{dias_restantes}"
                    if chave_notificacao not in self._notificacoes_enviadas_hoje[hoje]:
                        if self._enviar_notificacao_documento(documento, dias_restantes):
                            self._notificacoes_enviadas_hoje[hoje].add(chave_notificacao)
                            total_enviadas += 1

            logger.info(f"Total de notificações de documentos enviadas: {total_enviadas}")
            return total_enviadas

        except Exception as e:
            logger.error(f"Erro ao processar notificações de documentos: {str(e)}", exc_info=True)
            return 0

    def _obter_prazos_notificacao(self, documento):
        """Obtém os prazos de notificação para um documento"""
        # Primeiro tenta obter prazos específicos do documento
        if hasattr(documento, 'prazos_notificacao') and documento.prazos_notificacao:
            if isinstance(documento.prazos_notificacao, str):
                try:
                    return json.loads(documento.prazos_notificacao)
                except:
                    pass
            elif isinstance(documento.prazos_notificacao, list):
                return documento.prazos_notificacao
        
        # Se não houver prazos específicos, usa os padrões baseados no tipo
        if hasattr(documento, 'tipo') and documento.tipo:
            tipo_value = documento.tipo.value if hasattr(documento.tipo, 'value') else str(documento.tipo)
            
            # Prazos específicos por tipo de documento
            if 'licença' in tipo_value.lower() or 'ambiental' in tipo_value.lower():
                return [180, 120, 90, 60, 30, 15, 7]  # Licenças precisam mais antecedência
            elif 'contrato' in tipo_value.lower():
                return [90, 60, 30, 15, 7]
            elif 'certidão' in tipo_value.lower():
                return [60, 30, 15, 7, 3]
        
        # Retorna prazos padrão
        return self.PRAZOS_PADRAO

    def _enviar_notificacao_documento(self, documento, dias_restantes):
        """Envia notificação para um documento específico"""
        try:
            # Determina destinatários
            destinatarios = self._obter_destinatarios(documento)
            
            if not destinatarios:
                logger.warning(f"Documento {documento.id} sem destinatário para notificação")
                return False

            # Obtém nome do responsável
            responsavel_nome = self._obter_nome_responsavel(documento)
            
            # Link para visualização do documento
            link_documento = getattr(documento, 'link_visualizacao', None) or f"/documento/{documento.id}"

            # Monta e envia notificação
            assunto, corpo_html = formatar_email_notificacao(
                documento,
                dias_restantes,
                responsavel=responsavel_nome,
                link_documento=link_documento,
            )
            
            enviado = self.email_service.send_email(
                destinatarios, assunto, corpo_html, html=True
            )
            
            if enviado:
                logger.info(
                    f"Notificação enviada - Documento: {documento.id} ({documento.nome}), "
                    f"Dias restantes: {dias_restantes}, Destinatários: {destinatarios}"
                )
                
                # Registrar o envio (se houver modelo de histórico)
                self._registrar_envio(documento, destinatarios, dias_restantes)
            else:
                logger.error(
                    f"Falha ao enviar notificação - Documento: {documento.id}, "
                    f"Destinatários: {destinatarios}"
                )

            return enviado

        except Exception as e:
            logger.error(
                f"Erro ao enviar notificação para documento {documento.id}: {str(e)}",
                exc_info=True
            )
            return False

    def _obter_destinatarios(self, documento):
        """Obtém lista de e-mails para notificação"""
        destinatarios = []
        
        # Tenta obter do responsável
        responsavel = getattr(documento, "responsavel", None)
        if responsavel and getattr(responsavel, "email", None):
            destinatarios.append(responsavel.email)
        
        # Tenta obter de emails_notificacao
        if hasattr(documento, "emails_notificacao") and documento.emails_notificacao:
            if isinstance(documento.emails_notificacao, str):
                try:
                    emails = json.loads(documento.emails_notificacao)
                    if isinstance(emails, list):
                        destinatarios.extend(emails)
                except:
                    # Se não for JSON, tenta split por vírgula
                    destinatarios.extend([e.strip() for e in documento.emails_notificacao.split(',')])
            elif isinstance(documento.emails_notificacao, list):
                destinatarios.extend(documento.emails_notificacao)
        
        # Remove duplicatas e emails vazios
        destinatarios = list(set(e for e in destinatarios if e and '@' in e))
        
        return destinatarios

    def _obter_nome_responsavel(self, documento):
        """Obtém o nome do responsável pelo documento"""
        responsavel = getattr(documento, "responsavel", None)
        if responsavel:
            return getattr(responsavel, "nome", None) or getattr(responsavel, "email", "Responsável")
        return "Responsável"

    def _registrar_envio(self, documento, destinatarios, dias_restantes):
        """Registra o envio da notificação (implementar se necessário)"""
        # TODO: Implementar modelo de histórico de notificações para documentos
        # similar ao HistoricoNotificacao de endividamentos
        pass

    def configurar_prazos_documento(self, documento_id, prazos):
        """Configura prazos customizados para um documento"""
        try:
            documento = Documento.query.get(documento_id)
            if documento:
                # Salvar como JSON se o campo existir
                if hasattr(documento, 'prazos_notificacao'):
                    documento.prazos_notificacao = json.dumps(prazos)
                    db.session.commit()
                    return True
            return False
        except Exception as e:
            logger.error(f"Erro ao configurar prazos do documento {documento_id}: {str(e)}")
            db.session.rollback()
            return False


# Instância pronta para uso em tasks agendadas
notificacao_documento_service = NotificacaoDocumentoService()


# Task decorators para integração com Celery
def criar_task_verificar_documentos(celery_instance):
    """Cria a task do Celery para verificação de documentos"""
    @celery_instance.task(name='src.utils.notificacao_documentos_service.verificar_e_enviar_notificacoes_task')
    def verificar_e_enviar_notificacoes_task():
        """Task do Celery para verificar e enviar notificações de documentos"""
        return notificacao_documento_service.verificar_e_enviar_notificacoes()
    
    return verificar_e_enviar_notificacoes_task


def processar_notificacoes_documentos():
    """
    Função utilitária para ser usada em agendadores (Celery, cron, etc).
    """
    return notificacao_documento_service.verificar_e_enviar_notificacoes()