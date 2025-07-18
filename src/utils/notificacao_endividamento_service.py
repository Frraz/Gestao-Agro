# /src/utils/notificacao_endividamento_service.py

"""
Serviço para gerenciamento de notificações de endividamentos
Responsável por verificar, criar e enviar notificações para endividamentos com vencimento próximo
"""

import json
import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union, Any, Set

from sqlalchemy import and_, or_, func, desc

from src.models.db import db
from src.models.endividamento import Endividamento
from src.models.notificacao_endividamento import (
    HistoricoNotificacao,
    NotificacaoEndividamento
)
from src.utils.email_service import email_service, enviar_notificacao_lote
from src.utils.notificacao_utils import calcular_proximas_notificacoes_programadas

logger = logging.getLogger(__name__)


class NotificacaoEndividamentoService:
    """
    Serviço para gerenciar notificações de endividamentos
    
    Gerencia a criação, agendamento e envio de notificações para endividamentos 
    próximos do vencimento, utilizando configurações por endividamento.
    """

    # Intervalos de notificação em dias
    INTERVALOS_NOTIFICACAO = {
        "180_dias": 180,  # 6 meses
        "90_dias": 90,    # 3 meses
        "60_dias": 60,    # 2 meses
        "30_dias": 30,
        "15_dias": 15,
        "7_dias": 7,
        "3_dias": 3,
        "1_dia": 1,
        "0_dia": 0,       # No dia do vencimento
    }

    def __init__(self):
        self.email_service = email_service
        self._estatisticas = {
            "processadas": 0,
            "enviadas": 0,
            "falhas": 0,
            "criadas": 0
        }

    def verificar_e_enviar_notificacoes(self) -> int:
        """
        Verifica todos os endividamentos e envia notificações quando necessário
        
        Returns:
            Número total de notificações enviadas
        """
        self._estatisticas = {
            "processadas": 0,
            "enviadas": 0,
            "falhas": 0,
            "criadas": 0
        }
        notificacoes_enviadas = 0

        try:
            logger.info("Iniciando verificação de notificações de endividamento")
            
            # 1. Processar notificações já agendadas e pendentes
            notificacoes_enviadas += self._processar_notificacoes_pendentes()
            
            # 2. Criar novas notificações para endividamentos sem notificações agendadas
            self._criar_notificacoes_faltantes()
            
            # 3. Verificar notificações urgentes
            notificacoes_enviadas += self._processar_notificacoes_urgentes()
            
            self._estatisticas["enviadas"] = notificacoes_enviadas
            
            logger.info(
                f"Processamento concluído. {notificacoes_enviadas} notificações enviadas. "
                f"Estatísticas: {self._estatisticas}"
            )
            return notificacoes_enviadas

        except Exception as e:
            logger.error(f"Erro ao processar notificações de endividamento: {str(e)}", exc_info=True)
            return notificacoes_enviadas

    def _processar_notificacoes_pendentes(self) -> int:
        """
        Processa notificações que já deveriam ter sido enviadas
        
        Returns:
            Número de notificações enviadas
        """
        agora = datetime.utcnow()
        notificacoes_enviadas = 0
        
        try:
            # Buscar notificações pendentes que já passaram da data
            notificacoes_pendentes = NotificacaoEndividamento.query.filter(
                and_(
                    NotificacaoEndividamento.ativo == True,
                    NotificacaoEndividamento.enviado == False,
                    NotificacaoEndividamento.data_envio <= agora,
                    NotificacaoEndividamento.tentativas < 3,
                    NotificacaoEndividamento.tipo_notificacao != 'config'
                )
            ).all()
            
            total_pendentes = len(notificacoes_pendentes)
            self._estatisticas["processadas"] = total_pendentes
            
            logger.info(f"Processando {total_pendentes} notificações pendentes")
            
            # Preparar notificações para envio em lote
            emails_para_enviar = []
            
            for notificacao in notificacoes_pendentes:
                try:
                    email_data = self._preparar_notificacao_para_envio(notificacao)
                    if email_data:
                        emails_para_enviar.append(email_data)
                        notificacao.tentativas += 1
                except Exception as e:
                    logger.error(
                        f"Erro ao preparar notificação {notificacao.id}: {e}"
                    )
                    notificacao.tentativas += 1
                    notificacao.erro_mensagem = f"Erro na preparação: {str(e)}"
            
            # Enviar em lote se houver notificações
            if emails_para_enviar:
                stats = enviar_notificacao_lote(emails_para_enviar)
                notificacoes_enviadas = stats.get("enviados", 0)
                
                # Marcar notificações enviadas com sucesso
                for idx, email_data in enumerate(emails_para_enviar):
                    if idx < notificacoes_enviadas:
                        notificacao_id = email_data.get("meta", {}).get("notificacao_id")
                        if notificacao_id:
                            notificacao = db.session.query(NotificacaoEndividamento).get(notificacao_id)
                            if notificacao:
                                notificacao.enviado = True
                                notificacao.data_envio_realizado = datetime.utcnow()
                                self._registrar_historico(
                                    endividamento_id=notificacao.endividamento_id,
                                    notificacao_id=notificacao.id,
                                    tipo_notificacao=notificacao.tipo_notificacao,
                                    emails=json.loads(notificacao.emails) if isinstance(notificacao.emails, str) else notificacao.emails,
                                    sucesso=True
                                )
            
            # Commit das alterações
            db.session.commit()
            
            return notificacoes_enviadas
            
        except Exception as e:
            logger.error(f"Erro no processamento de notificações pendentes: {str(e)}", exc_info=True)
            db.session.rollback()
            return notificacoes_enviadas

    def _preparar_notificacao_para_envio(self, notificacao: NotificacaoEndividamento) -> Optional[Dict[str, Any]]:
        """
        Prepara os dados para envio de uma notificação
        
        Args:
            notificacao: Objeto NotificacaoEndividamento
            
        Returns:
            Dicionário com dados para envio ou None se não puder enviar
        """
        endividamento = notificacao.endividamento
        if not endividamento:
            logger.error(f"Endividamento não encontrado para notificação {notificacao.id}")
            return None
        
        emails = json.loads(notificacao.emails) if isinstance(notificacao.emails, str) else notificacao.emails
        
        if not emails:
            logger.warning(f"Sem emails configurados para notificação {notificacao.id}")
            return None
        
        # Extrair dias do tipo_notificacao
        try:
            dias = int(notificacao.tipo_notificacao.split('_')[0])
        except (ValueError, IndexError):
            dias = 0
        
        # Preparar email
        assunto, corpo = self._preparar_email(endividamento, notificacao.tipo_notificacao, dias)
        
        return {
            "destinatarios": emails,
            "assunto": assunto,
            "corpo": corpo,
            "html": True,
            "meta": {
                "notificacao_id": notificacao.id,
                "endividamento_id": endividamento.id,
                "dias_restantes": dias
            }
        }

    def _criar_notificacoes_faltantes(self) -> int:
        """
        Cria notificações para endividamentos que ainda não têm todas as notificações agendadas
        
        Returns:
            Número de novas notificações criadas
        """
        hoje = date.today()
        notificacoes_criadas = 0
        
        try:
            # Buscar endividamentos ativos com configuração de notificação
            endividamentos = db.session.query(Endividamento).join(
                NotificacaoEndividamento,
                and_(
                    NotificacaoEndividamento.endividamento_id == Endividamento.id,
                    NotificacaoEndividamento.tipo_notificacao == 'config',
                    NotificacaoEndividamento.ativo == True
                )
            ).filter(
                Endividamento.data_vencimento_final > hoje - timedelta(days=7)  # Incluir recém vencidos
            ).all()
            
            logger.info(f"Verificando notificações para {len(endividamentos)} endividamentos")
            
            for endividamento in endividamentos:
                novas = self._verificar_e_criar_notificacoes(endividamento)
                notificacoes_criadas += novas
            
            self._estatisticas["criadas"] = notificacoes_criadas
            logger.info(f"Criadas {notificacoes_criadas} novas notificações")
            
            return notificacoes_criadas
            
        except Exception as e:
            logger.error(f"Erro ao criar notificações faltantes: {str(e)}", exc_info=True)
            db.session.rollback()
            return 0

    def _verificar_e_criar_notificacoes(self, endividamento: Endividamento) -> int:
        """
        Verifica e cria notificações faltantes para um endividamento
        
        Args:
            endividamento: Objeto Endividamento
            
        Returns:
            Número de novas notificações criadas
        """
        novas_criadas = 0
        
        try:
            # Obter configuração de emails
            config = NotificacaoEndividamento.query.filter_by(
                endividamento_id=endividamento.id,
                tipo_notificacao='config',
                ativo=True
            ).first()
            
            if not config or not config.emails:
                return 0
            
            # Obter prazos já enviados e agendados
            notificacoes_existentes = NotificacaoEndividamento.query.filter(
                NotificacaoEndividamento.endividamento_id == endividamento.id,
                NotificacaoEndividamento.tipo_notificacao != 'config',
                NotificacaoEndividamento.ativo == True
            ).all()
            
            prazos_existentes = set()
            for n in notificacoes_existentes:
                # Extrair número de dias do tipo_notificacao (ex: '30_dias' -> 30)
                try:
                    dias = int(n.tipo_notificacao.split('_')[0])
                    prazos_existentes.add(dias)
                except (ValueError, IndexError):
                    pass
            
            # Usar notificacao_utils para calcular próximas notificações
            prazos = list(self.INTERVALOS_NOTIFICACAO.values())
            proximas = calcular_proximas_notificacoes_programadas(
                endividamento.data_vencimento_final,
                prazos,
                enviados=list(prazos_existentes)
            )
            
            # Criar notificações para as próximas não agendadas
            for notif in proximas:
                prazo = notif['prazo']
                tipo_notificacao = f"{prazo}_dias" if prazo != 1 else "1_dia"
                if prazo == 0:
                    tipo_notificacao = "0_dia"
                
                # Verificar se já existe notificação agendada
                existe = NotificacaoEndividamento.query.filter_by(
                    endividamento_id=endividamento.id,
                    tipo_notificacao=tipo_notificacao,
                    ativo=True
                ).first()
                
                if not existe:
                    nova_notificacao = NotificacaoEndividamento(
                        endividamento_id=endividamento.id,
                        tipo_notificacao=tipo_notificacao,
                        data_envio=notif['envio'],
                        emails=config.emails,
                        enviado=False,
                        ativo=True
                    )
                    db.session.add(nova_notificacao)
                    novas_criadas += 1
                    logger.debug(
                        f"Criada notificação {tipo_notificacao} "
                        f"para endividamento {endividamento.id} em {notif['envio']}"
                    )
            
            if novas_criadas > 0:
                db.session.commit()
            
            return novas_criadas
            
        except Exception as e:
            logger.error(f"Erro ao criar notificações para endividamento {endividamento.id}: {e}")
            db.session.rollback()
            return 0

    def _processar_notificacoes_urgentes(self) -> int:
        """
        Processa notificações urgentes para endividamentos que vencem muito em breve
        
        Returns:
            Número de notificações urgentes enviadas
        """
        hoje = date.today()
        amanha = hoje + timedelta(days=1)
        notificacoes_enviadas = 0
        
        try:
            # Buscar endividamentos que vencem hoje ou amanhã e não tiveram notificação enviada hoje
            endividamentos_urgentes = db.session.query(Endividamento).outerjoin(
                HistoricoNotificacao,
                and_(
                    HistoricoNotificacao.endividamento_id == Endividamento.id,
                    func.date(HistoricoNotificacao.data_envio) == hoje
                )
            ).filter(
                or_(
                    Endividamento.data_vencimento_final == hoje,
                    Endividamento.data_vencimento_final == amanha
                ),
                HistoricoNotificacao.id.is_(None)  # Não teve notificação hoje
            ).all()
            
            if not endividamentos_urgentes:
                return 0
            
            logger.info(f"Processando {len(endividamentos_urgentes)} notificações urgentes")
            
            emails_para_enviar = []
            
            for endividamento in endividamentos_urgentes:
                # Verificar se tem configuração de emails
                config = NotificacaoEndividamento.query.filter_by(
                    endividamento_id=endividamento.id,
                    tipo_notificacao='config',
                    ativo=True
                ).first()
                
                if not config or not config.emails:
                    continue
                
                # Preparar email urgente
                dias = (endividamento.data_vencimento_final - hoje).days
                
                if dias == 0:
                    tipo = "0_dia"  # Vence hoje
                    assunto = f"🚨 URGENTE: Endividamento vence HOJE - {endividamento.banco}"
                else:
                    tipo = "1_dia"  # Vence amanhã
                    assunto = f"🚨 URGENTE: Endividamento vence AMANHÃ - {endividamento.banco}"
                
                _, corpo = self._preparar_email(
                    endividamento, 
                    tipo, 
                    dias, 
                    urgente=True
                )
                
                emails = json.loads(config.emails) if isinstance(config.emails, str) else config.emails
                
                emails_para_enviar.append({
                    "destinatarios": emails,
                    "assunto": assunto,
                    "corpo": corpo,
                    "html": True,
                    "meta": {
                        "endividamento_id": endividamento.id,
                        "dias_restantes": dias,
                        "urgente": True
                    }
                })
            
            # Enviar notificações urgentes
            if emails_para_enviar:
                stats = enviar_notificacao_lote(emails_para_enviar, batch_size=5)
                notificacoes_enviadas = stats.get("enviados", 0)
                
                # Registrar histórico para cada envio bem-sucedido
                for idx, email_data in enumerate(emails_para_enviar):
                    if idx < notificacoes_enviadas:
                        endividamento_id = email_data.get("meta", {}).get("endividamento_id")
                        dias = email_data.get("meta", {}).get("dias_restantes", 0)
                        tipo = "0_dia" if dias == 0 else "1_dia"
                        
                        self._registrar_historico(
                            endividamento_id=endividamento_id,
                            notificacao_id=None,
                            tipo_notificacao=f"urgente_{tipo}",
                            emails=email_data.get("destinatarios", []),
                            sucesso=True
                        )
            
            db.session.commit()
            return notificacoes_enviadas
            
        except Exception as e:
            logger.error(f"Erro ao processar notificações urgentes: {e}", exc_info=True)
            db.session.rollback()
            return 0

    def _preparar_email(self, endividamento: Endividamento, tipo_notificacao: str, 
                       dias: int, urgente: bool = False) -> Tuple[str, str]:
        """
        Prepara o assunto e corpo do e-mail
        
        Args:
            endividamento: Objeto Endividamento
            tipo_notificacao: Tipo da notificação (ex: '30_dias')
            dias: Número de dias até o vencimento
            urgente: Se é uma notificação urgente
            
        Returns:
            Tupla (assunto, corpo_html) do email
        """
        # Formatar período para o assunto
        if dias > 0:
            if dias >= 30:
                if dias == 180:
                    periodo = "6 meses"
                elif dias == 90:
                    periodo = "3 meses"
                elif dias == 60:
                    periodo = "2 meses"
                else:
                    periodo = f"{dias} dias"
            else:
                periodo = f"{dias} dia{'s' if dias > 1 else ''}"
            
            assunto = f"{'🚨 URGENTE: ' if urgente else ''}Endividamento vence em {periodo} - {endividamento.banco}"
        elif dias == 0:
            periodo = "HOJE"
            assunto = f"{'🚨 URGENTE: ' if urgente else ''}Endividamento vence HOJE - {endividamento.banco}"
        else:
            # Vencido
            dias_atraso = abs(dias)
            periodo = f"{dias_atraso} dia{'s' if dias_atraso > 1 else ''} ATRÁS"
            assunto = f"{'🚨 URGENTE: ' if urgente else ''}Endividamento VENCIDO há {periodo} - {endividamento.banco}"

        # Calcular valor total das parcelas pendentes
        valor_total_pendente = sum(
            parcela.valor for parcela in endividamento.parcelas if not parcela.pago
        )

        # Preparar lista de pessoas
        pessoas_nomes = [pessoa.nome for pessoa in endividamento.pessoas] if hasattr(endividamento, 'pessoas') else []
        
        # Definir cores baseadas na urgência e dias
        if dias <= 0:
            # Vencido ou vence hoje
            cor_cabecalho = "#d32f2f"  # Vermelho
            cor_alerta = "#ffebee"      # Vermelho claro
            borda_alerta = "#d32f2f"
            emoji = "🚨"
        elif dias <= 3:
            # Urgente (1-3 dias)
            cor_cabecalho = "#ff5722"  # Laranja escuro
            cor_alerta = "#fff3e0"     # Laranja claro
            borda_alerta = "#ff5722"
            emoji = "⚠️"
        elif dias <= 7:
            # Atenção (4-7 dias)
            cor_cabecalho = "#ff9800"  # Laranja
            cor_alerta = "#fff8e1"     # Amarelo claro
            borda_alerta = "#ff9800"
            emoji = "⚠️"
        elif dias <= 30:
            # Aviso (8-30 dias)
            cor_cabecalho = "#2196f3"  # Azul
            cor_alerta = "#e3f2fd"     # Azul claro
            borda_alerta = "#2196f3"
            emoji = "ℹ️"
        else:
            # Informativo (>30 dias)
            cor_cabecalho = "#4caf50"  # Verde
            cor_alerta = "#e8f5e9"     # Verde claro
            borda_alerta = "#4caf50"
            emoji = "📆"

        corpo = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: {cor_cabecalho}; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #ffffff; padding: 20px; border: 1px solid #ddd; border-top: none; border-radius: 0 0 5px 5px; }}
                .info-box {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .alert-box {{ background-color: {cor_alerta}; border: 2px solid {borda_alerta}; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .footer {{ font-size: 12px; color: #666; margin-top: 30px; text-align: center; }}
                .label {{ font-weight: bold; width: 40%; display: inline-block; }}
                .value {{ width: 60%; display: inline-block; }}
                ul {{ list-style-type: none; padding-left: 0; }}
                li {{ padding: 5px 0; }}
                @media only screen and (max-width: 600px) {{
                    .label, .value {{ display: block; width: 100%; }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>{emoji} {'NOTIFICAÇÃO URGENTE' if urgente else 'Lembrete de Vencimento'}</h2>
                    <h3>Endividamento vencendo em {periodo}</h3>
                </div>
                <div class="content">
                    <p>Este é um lembrete automático sobre um endividamento com vencimento {
                    'HOJE' if dias == 0 else f'em {periodo}' if dias > 0 else f'há {periodo}'
                    }.</p>
                    
                    <div class="info-box">
                        <h3 style="margin-top: 0; color: {cor_cabecalho};">Detalhes do Endividamento:</h3>
                        <ul>
                            <li><span class="label">Banco:</span> <span class="value">{endividamento.banco}</span></li>
                            <li><span class="label">Número da Proposta:</span> <span class="value">{endividamento.numero_proposta or 'N/A'}</span></li>
                            <li><span class="label">Data de Vencimento:</span> <span class="value">{endividamento.data_vencimento_final.strftime('%d/%m/%Y')}</span></li>
                            <li><span class="label">Taxa de Juros:</span> <span class="value">{endividamento.taxa_juros}% {'a.a.' if getattr(endividamento, 'tipo_taxa_juros', None) == 'ano' else 'a.m.'}</span></li>
                            {f'<li><span class="label">Valor da Operação:</span> <span class="value">R$ {endividamento.valor_operacao:,.2f}</span></li>' if getattr(endividamento, 'valor_operacao', None) else ''}
                            <li><span class="label">Valor Total Pendente:</span> <span class="value">R$ {valor_total_pendente:,.2f}</span></li>
                            {f'<li><span class="label">Pessoas Vinculadas:</span> <span class="value">{", ".join(pessoas_nomes)}</span></li>' if pessoas_nomes else ''}
                        </ul>
                    </div>
                    
                    <div class="alert-box">
                        <p style="margin: 0;"><strong>{emoji} {'ATENÇÃO URGENTE:' if urgente else 'Atenção:'}</strong> {
                        'Este endividamento vence HOJE. Providências imediatas são necessárias!' if dias == 0 else 
                        'Este endividamento está VENCIDO. Ação imediata é necessária!' if dias < 0 else
                        'Certifique-se de que todas as providências necessárias foram tomadas para o pagamento dentro do prazo.'
                        }</p>
                    </div>
                    
                    {'<p><strong>Observação:</strong> Esta é uma notificação urgente automaticamente gerada devido à proximidade do vencimento. Por favor, verifique e tome as devidas providências o mais rápido possível.</p>' if urgente else ''}
                    
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                    
                    <div class="footer">
                        <p>Este é um e-mail automático do Sistema de Gestão Agrícola. Não responda a este e-mail.</p>
                        <p>Data de envio: {datetime.now().strftime('%d/%m/%Y às %H:%M')}</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        return assunto, corpo

    def _registrar_historico(self, endividamento_id: int, notificacao_id: Optional[int], 
                           tipo_notificacao: str, emails: List[str], 
                           sucesso: bool, erro_mensagem: Optional[str] = None) -> None:
        """
        Registra o envio da notificação no histórico
        
        Args:
            endividamento_id: ID do endividamento
            notificacao_id: ID da notificação ou None
            tipo_notificacao: Tipo da notificação
            emails: Lista de emails para os quais a notificação foi enviada
            sucesso: Se o envio foi bem-sucedido
            erro_mensagem: Mensagem de erro, se houver
        """
        try:
            historico = HistoricoNotificacao(
                endividamento_id=endividamento_id,
                notificacao_id=notificacao_id,
                tipo_notificacao=tipo_notificacao,
                emails_enviados=json.dumps(emails) if isinstance(emails, list) else emails,
                sucesso=sucesso,
                erro_mensagem=erro_mensagem,
            )

            db.session.add(historico)
            # Não faz commit aqui pois já é feito no método chamador

        except Exception as e:
            logger.error(f"Erro ao registrar histórico: {str(e)}")

    def configurar_notificacao(self, endividamento_id: int, emails: List[str], ativo: bool = True) -> bool:
        """
        Configura ou atualiza as notificações para um endividamento
        
        Args:
            endividamento_id: ID do endividamento
            emails: Lista de emails para receber notificações
            ativo: Se as notificações devem estar ativas
            
        Returns:
            Sucesso da operação
        """
        try:
            # Desativar configurações antigas
            NotificacaoEndividamento.query.filter_by(
                endividamento_id=endividamento_id,
                tipo_notificacao='config'
            ).update({'ativo': False})
            
            if ativo and emails:
                # Validar emails
                emails = [email for email in emails if email and '@' in email]
                
                if not emails:
                    logger.warning(f"Nenhum email válido para configuração do endividamento {endividamento_id}")
                    return False
                
                # Criar nova configuração
                config = NotificacaoEndividamento(
                    endividamento_id=endividamento_id,
                    tipo_notificacao='config',
                    data_envio=datetime.utcnow(),
                    emails=json.dumps(emails),
                    enviado=True,  # Marcar como enviado pois é só configuração
                    ativo=True
                )
                db.session.add(config)
                db.session.commit()
                
                # Criar notificações agendadas
                endividamento = Endividamento.query.get(endividamento_id)
                if endividamento:
                    self._verificar_e_criar_notificacoes(endividamento)
            else:
                # Desativar todas as notificações do endividamento
                NotificacaoEndividamento.query.filter_by(
                    endividamento_id=endividamento_id
                ).update({'ativo': False})
                db.session.commit()
            
            logger.info(f"Configuração atualizada para endividamento {endividamento_id}")
            return True

        except Exception as e:
            logger.error(f"Erro ao configurar notificações: {str(e)}")
            db.session.rollback()
            return False

    def obter_proximas_notificacoes(self, endividamento_id: int) -> List[Dict[str, Any]]:
        """
        Retorna as próximas notificações programadas para um endividamento
        
        Args:
            endividamento_id: ID do endividamento
            
        Returns:
            Lista de dicionários com informações das próximas notificações
        """
        try:
            endividamento = Endividamento.query.get(endividamento_id)
            if not endividamento:
                return []
            
            # Verificar se notificações estão configuradas
            config = NotificacaoEndividamento.query.filter_by(
                endividamento_id=endividamento_id,
                tipo_notificacao='config',
                ativo=True
            ).first()
            
            if not config:
                return []
            
            # Obter notificações já enviadas
            enviadas = NotificacaoEndividamento.query.filter_by(
                endividamento_id=endividamento_id,
                enviado=True
            ).all()
            
            prazos_enviados = []
            for n in enviadas:
                try:
                    dias = int(n.tipo_notificacao.split('_')[0])
                    prazos_enviados.append(dias)
                except (ValueError, IndexError):
                    pass
            
            # Calcular próximas usando o utilitário
            prazos = list(self.INTERVALOS_NOTIFICACAO.values())
            proximas = calcular_proximas_notificacoes_programadas(
                endividamento.data_vencimento_final,
                prazos,
                enviados=prazos_enviados
            )
            
            # Adicionar informações de emails
            emails = json.loads(config.emails) if isinstance(config.emails, str) else config.emails
            
            for notif in proximas:
                notif['emails'] = emails
                notif['config_ativa'] = True
            
            return proximas
            
        except Exception as e:
            logger.error(f"Erro ao obter próximas notificações: {str(e)}")
            return []

    def limpar_notificacoes_antigas(self, dias: int = 90) -> int:
        """
        Remove notificações antigas do sistema
        
        Args:
            dias: Notificações com mais de X dias serão removidas
            
        Returns:
            Número de notificações removidas
        """
        try:
            data_limite = datetime.utcnow() - timedelta(days=dias)
            
            # Contar notificações antigas (exceto configurações)
            antigas = NotificacaoEndividamento.query.filter(
                NotificacaoEndividamento.data_envio < data_limite,
                NotificacaoEndividamento.tipo_notificacao != 'config'
            ).count()
            
            if antigas > 0:
                # Remover notificações antigas
                NotificacaoEndividamento.query.filter(
                    NotificacaoEndividamento.data_envio < data_limite,
                    NotificacaoEndividamento.tipo_notificacao != 'config'
                ).delete(synchronize_session=False)
                
                db.session.commit()
                logger.info(f"Removidas {antigas} notificações antigas")
            
            return antigas
            
        except Exception as e:
            logger.error(f"Erro ao limpar notificações antigas: {str(e)}")
            db.session.rollback()
            return 0

    def obter_estatisticas(self) -> Dict[str, Any]:
        """
        Retorna estatísticas sobre notificações
        
        Returns:
            Dicionário com estatísticas
        """
        try:
            hoje = datetime.utcnow().date()
            inicio_mes = datetime(hoje.year, hoje.month, 1).date()
            
            # Estatísticas gerais
            total_notificacoes = db.session.query(func.count(NotificacaoEndividamento.id)).scalar()
            
            # Notificações enviadas hoje
            enviadas_hoje = db.session.query(func.count(HistoricoNotificacao.id)).filter(
                func.date(HistoricoNotificacao.data_envio) == hoje
            ).scalar()
            
            # Notificações enviadas este mês
            enviadas_mes = db.session.query(func.count(HistoricoNotificacao.id)).filter(
                func.date(HistoricoNotificacao.data_envio) >= inicio_mes
            ).scalar()
            
            # Notificações pendentes
            pendentes = db.session.query(func.count(NotificacaoEndividamento.id)).filter(
                NotificacaoEndividamento.enviado == False,
                NotificacaoEndividamento.ativo == True,
                NotificacaoEndividamento.tipo_notificacao != 'config'
            ).scalar()
            
            # Notificações para enviar hoje
            hoje_utc = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            amanha_utc = hoje_utc + timedelta(days=1)
            para_hoje = db.session.query(func.count(NotificacaoEndividamento.id)).filter(
                NotificacaoEndividamento.enviado == False,
                NotificacaoEndividamento.ativo == True,
                NotificacaoEndividamento.data_envio >= hoje_utc,
                NotificacaoEndividamento.data_envio < amanha_utc,
                NotificacaoEndividamento.tipo_notificacao != 'config'
            ).scalar()
            
            return {
                "total_notificacoes": total_notificacoes,
                "enviadas_hoje": enviadas_hoje,
                "enviadas_mes": enviadas_mes,
                "pendentes": pendentes,
                "para_hoje": para_hoje,
                "ultima_execucao": self._estatisticas
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {str(e)}")
            return {
                "erro": str(e),
                "ultima_execucao": self._estatisticas
            }


# Instância pronta para uso em tasks agendadas
notificacao_endividamento_service = NotificacaoEndividamentoService()


def processar_notificacoes_endividamentos() -> int:
    """
    Função utilitária para ser usada em agendadores (Celery, cron, etc).
    
    Returns:
        Número total de notificações enviadas
    """
    return notificacao_endividamento_service.verificar_e_enviar_notificacoes()


def limpar_notificacoes_antigas(dias: int = 90) -> int:
    """
    Remove notificações antigas do sistema.
    
    Args:
        dias: Notificações com mais de X dias serão removidas
        
    Returns:
        Número de notificações removidas
    """
    return notificacao_endividamento_service.limpar_notificacoes_antigas(dias)