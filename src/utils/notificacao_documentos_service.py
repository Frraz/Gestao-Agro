# /src/utils/notificacao_documentos_service.py

"""
Serviço de Notificações para Documentos
Gerencia o processamento e envio de notificações automáticas para documentos próximos do vencimento
"""
import datetime
import logging
import json
from typing import List, Dict, Set, Any, Optional, Union, Tuple
from collections import defaultdict
from sqlalchemy import and_, or_

from src.models.db import db
from src.models.documento import Documento
from src.utils.email_service import email_service, formatar_email_notificacao, enviar_notificacao_lote

logger = logging.getLogger(__name__)


class NotificacaoDocumentoService:
    """
    Serviço para gerenciar notificações automáticas de vencimento de documentos.
    """
    
    # Prazos padrão de notificação em dias
    PRAZOS_PADRAO = [90, 60, 30, 15, 7, 3, 1]
    
    # Prazos específicos por tipo de documento
    PRAZOS_POR_TIPO = {
        'licenca': [180, 120, 90, 60, 30, 15, 7],
        'ambiental': [180, 120, 90, 60, 30, 15, 7],
        'contrato': [90, 60, 30, 15, 7],
        'certidao': [60, 30, 15, 7, 3],
        'gta': [30, 15, 7, 3, 1],
    }

    def __init__(self):
        self.email_service = email_service
        self._notificacoes_enviadas_hoje = defaultdict(set)
        self._documentos_cache = {}
        
    def verificar_e_enviar_notificacoes(self) -> int:
        """
        Verifica todos os documentos com prazos de notificação e envia e-mails quando necessário.
        
        Returns:
            Número total de notificações enviadas.
        """
        hoje = datetime.date.today()
        total_enviadas = 0
        emails_para_enviar = []

        try:
            # Buscar documentos relevantes - tanto os que estão próximos de vencer
            # quanto os já vencidos (para notificações de atraso)
            documentos = self._buscar_documentos_relevantes(hoje)

            logger.info(f"Verificando {len(documentos)} documentos para notificações")
            
            for documento in documentos:
                # Calcula dias restantes para o vencimento (pode ser negativo para vencidos)
                dias_restantes = (documento.data_vencimento - hoje).days
                
                # Determina os prazos de notificação para este documento
                prazos = self._obter_prazos_notificacao(documento)
                
                # Verifica se deve enviar notificação hoje
                if self._deve_notificar(documento, dias_restantes, prazos, hoje):
                    # Prepara email para envio em lote
                    email_data = self._preparar_notificacao(documento, dias_restantes)
                    if email_data:
                        emails_para_enviar.append(email_data)
                        # Registramos que este documento foi processado hoje
                        chave_notificacao = f"{documento.id}_{dias_restantes}"
                        self._notificacoes_enviadas_hoje[hoje].add(chave_notificacao)
                        total_enviadas += 1

            # Envia emails em lote para melhor performance
            if emails_para_enviar:
                stats = enviar_notificacao_lote(emails_para_enviar)
                logger.info(f"Resultado do envio em lote: {stats}")

            logger.info(f"Total de notificações de documentos enviadas: {total_enviadas}")
            return total_enviadas

        except Exception as e:
            logger.error(f"Erro ao processar notificações de documentos: {str(e)}", exc_info=True)
            return 0

    def _buscar_documentos_relevantes(self, hoje: datetime.date) -> List[Documento]:
        """Busca documentos que podem precisar de notificação hoje"""
        try:
            # Construir janela de tempo - desde documentos vencidos até os que vencem 
            # dentro do prazo máximo de notificação (tipicamente 180 dias)
            prazo_maximo = max(self.PRAZOS_PADRAO + 
                              [prazo for prazos in self.PRAZOS_POR_TIPO.values() for prazo in prazos])
            
            data_limite = hoje + datetime.timedelta(days=prazo_maximo)
            
            # Otimização: buscar apenas documentos que vencem até a data limite
            # ou que já venceram (para notificações de atraso)
            documentos = Documento.query.filter(
                Documento.data_vencimento.isnot(None),
                or_(
                    # Documentos próximos de vencer
                    and_(
                        Documento.data_vencimento >= hoje,
                        Documento.data_vencimento <= data_limite
                    ),
                    # Documentos vencidos há no máximo 30 dias (para notificações de atraso)
                    and_(
                        Documento.data_vencimento < hoje,
                        Documento.data_vencimento >= hoje - datetime.timedelta(days=30)
                    )
                )
            ).all()
            
            return documentos
            
        except Exception as e:
            logger.error(f"Erro ao buscar documentos: {str(e)}", exc_info=True)
            return []

    def _deve_notificar(self, documento: Documento, dias_restantes: int, prazos: List[int], hoje: datetime.date) -> bool:
        """Verifica se o documento deve ser notificado hoje"""
        # Para documentos vencidos (dias negativos), convertemos para categoria 0
        dias_categoria = max(0, dias_restantes)
        
        # Caso específico para vencido (dias_restantes < 0)
        if dias_restantes < 0:
            # Notificação de atraso:
            # - No primeiro dia de atraso (dias_restantes == -1)
            # - A cada 7 dias de atraso (-7, -14, -21, -28...)
            return dias_restantes == -1 or (dias_restantes < 0 and dias_restantes % 7 == 0)
        
        # Para documentos que vão vencer, verificar se o dia está nos prazos
        if dias_restantes in prazos:
            # Evita enviar múltiplas notificações para o mesmo documento no mesmo dia
            chave_notificacao = f"{documento.id}_{dias_restantes}"
            return chave_notificacao not in self._notificacoes_enviadas_hoje[hoje]
            
        return False

    def _obter_prazos_notificacao(self, documento: Documento) -> List[int]:
        """Obtém os prazos de notificação para um documento"""
        # Primeiro tenta obter prazos específicos do documento
        if hasattr(documento, 'prazos_notificacao') and documento.prazos_notificacao:
            if isinstance(documento.prazos_notificacao, str):
                try:
                    return json.loads(documento.prazos_notificacao)
                except json.JSONDecodeError:
                    logger.warning(f"Formato inválido em prazos_notificacao do documento {documento.id}")
            elif isinstance(documento.prazos_notificacao, list):
                return documento.prazos_notificacao
        
        # Se não houver prazos específicos, usa os padrões baseados no tipo
        if hasattr(documento, 'tipo') and documento.tipo:
            tipo_value = documento.tipo.value if hasattr(documento.tipo, 'value') else str(documento.tipo)
            tipo_value = tipo_value.lower()
            
            # Verificar cada tipo conhecido
            for tipo_chave, prazos in self.PRAZOS_POR_TIPO.items():
                if tipo_chave in tipo_value:
                    return prazos
        
        # Retorna prazos padrão
        return self.PRAZOS_PADRAO

    def _preparar_notificacao(self, documento: Documento, dias_restantes: int) -> Optional[Dict]:
        """
        Prepara os dados para uma notificação de documento
        
        Returns:
            Dicionário com dados do email ou None se não for possível enviar
        """
        try:
            # Determina destinatários
            destinatarios = self._obter_destinatarios(documento)
            
            if not destinatarios:
                logger.warning(f"Documento {documento.id} sem destinatário para notificação")
                return None

            # Obtém nome do responsável
            responsavel_nome = self._obter_nome_responsavel(documento)
            
            # Link para visualização do documento
            link_documento = getattr(documento, 'link_visualizacao', None) or f"/documento/{documento.id}"

            # Monta a notificação
            assunto, corpo_html = formatar_email_notificacao(
                documento,
                dias_restantes,
                responsavel=responsavel_nome,
                link_documento=link_documento,
            )
            
            # Registrar o envio no histórico (sem importar o modelo)
            self._registrar_envio_simples(documento, destinatarios, dias_restantes)
            
            # Retorna dados para envio
            return {
                "destinatarios": destinatarios,
                "assunto": assunto,
                "corpo": corpo_html,
                "html": True,
                "meta": {
                    "documento_id": documento.id,
                    "dias_restantes": dias_restantes,
                    "nome_documento": documento.nome if hasattr(documento, "nome") else "Documento"
                }
            }

        except Exception as e:
            logger.error(
                f"Erro ao preparar notificação para documento {documento.id}: {str(e)}",
                exc_info=True
            )
            return None

    def _obter_destinatarios(self, documento: Documento) -> List[str]:
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
                except json.JSONDecodeError:
                    # Se não for JSON, tenta split por vírgula
                    destinatarios.extend([e.strip() for e in documento.emails_notificacao.split(',')])
            elif isinstance(documento.emails_notificacao, list):
                destinatarios.extend(documento.emails_notificacao)
        
        # Adicionar emails dos usuários associados à entidade
        # (depende da estrutura do modelo)
        if hasattr(documento, "entidade_emails") and callable(getattr(documento, "entidade_emails", None)):
            entidade_emails = documento.entidade_emails()
            if entidade_emails:
                destinatarios.extend(entidade_emails)
        
        # Remove duplicatas e emails vazios
        destinatarios = list(set(e for e in destinatarios if e and '@' in e))
        
        return destinatarios

    def _obter_nome_responsavel(self, documento: Documento) -> str:
        """Obtém o nome do responsável pelo documento"""
        responsavel = getattr(documento, "responsavel", None)
        if responsavel:
            return getattr(responsavel, "nome", None) or getattr(responsavel, "email", "Responsável")
        return "Responsável"

    def _registrar_envio_simples(self, documento: Documento, destinatarios: List[str], dias_restantes: int) -> None:
        """
        Registra o envio da notificação apenas no log 
        (implementação simplificada sem depender de modelo externo)
        """
        try:
            logger.info(
                f"Notificação enviada - Documento: {documento.id} ({getattr(documento, 'nome', 'N/A')}), "
                f"Dias restantes: {dias_restantes}, Destinatários: {len(destinatarios)}"
            )
            
            # Lógica adicional de registro pode ser implementada aqui
            # sem depender de modelos externos
            
        except Exception as e:
            logger.error(f"Erro ao registrar envio de notificação: {e}")

    def configurar_prazos_documento(self, documento_id: int, prazos: List[int]) -> bool:
        """
        Configura prazos customizados para um documento
        
        Args:
            documento_id: ID do documento
            prazos: Lista de prazos em dias
            
        Returns:
            Sucesso da operação
        """
        try:
            # Validar prazos
            prazos = [int(p) for p in prazos if int(p) >= 0]
            if not prazos:
                logger.error(f"Lista de prazos vazia ou inválida para documento {documento_id}")
                return False
                
            documento = Documento.query.get(documento_id)
            if documento:
                # Salvar como JSON se o campo existir
                if hasattr(documento, 'prazos_notificacao'):
                    documento.prazos_notificacao = json.dumps(prazos)
                    db.session.commit()
                    
                    # Atualizar cache se existir
                    if documento_id in self._documentos_cache:
                        self._documentos_cache.pop(documento_id)
                        
                    return True
                else:
                    logger.warning(f"Campo prazos_notificacao não existe no modelo Documento")
            return False
        except Exception as e:
            logger.error(f"Erro ao configurar prazos do documento {documento_id}: {str(e)}")
            db.session.rollback()
            return False
            
    def processar_documentos_vencidos(self) -> int:
        """
        Processa documentos já vencidos para notificação de atraso
        
        Returns:
            Número de notificações enviadas
        """
        hoje = datetime.date.today()
        total_enviadas = 0
        emails_para_enviar = []

        try:
            # Buscar documentos vencidos recentemente (últimos 30 dias)
            documentos_vencidos = Documento.query.filter(
                Documento.data_vencimento.isnot(None),
                Documento.data_vencimento < hoje,
                Documento.data_vencimento >= hoje - datetime.timedelta(days=30)
            ).all()
            
            logger.info(f"Verificando {len(documentos_vencidos)} documentos vencidos")
            
            for documento in documentos_vencidos:
                dias_restantes = (documento.data_vencimento - hoje).days  # Valor negativo
                
                # Notificar no primeiro dia (-1) e depois a cada 7 dias
                if dias_restantes == -1 or (dias_restantes % 7 == 0):
                    email_data = self._preparar_notificacao(documento, dias_restantes)
                    if email_data:
                        emails_para_enviar.append(email_data)
                        total_enviadas += 1
            
            # Enviar em lote
            if emails_para_enviar:
                stats = enviar_notificacao_lote(emails_para_enviar)
                logger.info(f"Documentos vencidos: {stats}")
                
            return total_enviadas
            
        except Exception as e:
            logger.error(f"Erro ao processar documentos vencidos: {e}", exc_info=True)
            return 0
            
    def limpar_cache(self) -> None:
        """Limpa o cache de documentos"""
        self._documentos_cache.clear()
        self._notificacoes_enviadas_hoje.clear()


# Instância pronta para uso em tasks agendadas
notificacao_documento_service = NotificacaoDocumentoService()


def processar_notificacoes_documentos() -> int:
    """
    Função utilitária para ser usada em agendadores (Celery, cron, etc).
    Processa tanto documentos prestes a vencer quanto vencidos.
    
    Returns:
        Número total de notificações enviadas
    """
    service = notificacao_documento_service
    
    # Processar documentos prestes a vencer
    notif_proximas = service.verificar_e_enviar_notificacoes()
    
    # Processar documentos já vencidos
    notif_vencidas = service.processar_documentos_vencidos()
    
    return notif_proximas + notif_vencidas