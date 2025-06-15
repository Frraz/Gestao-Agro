# Serviço de Notificações para Endividamentos
from datetime import datetime, date, timedelta
from sqlalchemy import and_
from src.models.db import db
from src.models.endividamento import Endividamento
from src.models.notificacao_endividamento import NotificacaoEndividamento, HistoricoNotificacao
from src.utils.email_service import EmailService
import json
import logging

logger = logging.getLogger(__name__)

class NotificacaoEndividamentoService:
    """Serviço para gerenciar notificações de endividamentos"""
    
    # Intervalos de notificação em dias
    INTERVALOS_NOTIFICACAO = {
        '6_meses': 180,
        '3_meses': 90,
        '30_dias': 30,
        '15_dias': 15,
        '7_dias': 7,
        '3_dias': 3,
        '1_dia': 1
    }
    
    def __init__(self):
        self.email_service = EmailService()
    
    def verificar_e_enviar_notificacoes(self):
        """Verifica todos os endividamentos e envia notificações quando necessário"""
        hoje = date.today()
        notificacoes_enviadas = 0
        
        try:
            # Buscar todos os endividamentos ativos com notificações configuradas
            endividamentos = db.session.query(Endividamento).join(
                NotificacaoEndividamento
            ).filter(
                NotificacaoEndividamento.ativo == True,
                Endividamento.data_vencimento_final > hoje
            ).all()
            
            for endividamento in endividamentos:
                notificacoes_enviadas += self._processar_endividamento(endividamento, hoje)
            
            logger.info(f"Processamento de notificações concluído. {notificacoes_enviadas} notificações enviadas.")
            return notificacoes_enviadas
            
        except Exception as e:
            logger.error(f"Erro ao processar notificações: {str(e)}")
            return 0
    
    def _processar_endividamento(self, endividamento, hoje):
        """Processa um endividamento específico para verificar se precisa enviar notificações"""
        notificacoes_enviadas = 0
        dias_para_vencimento = (endividamento.data_vencimento_final - hoje).days
        
        for tipo_notificacao, dias_antecedencia in self.INTERVALOS_NOTIFICACAO.items():
            if dias_para_vencimento == dias_antecedencia:
                if not self._ja_foi_enviada(endividamento.id, tipo_notificacao):
                    if self._enviar_notificacao(endividamento, tipo_notificacao):
                        notificacoes_enviadas += 1
        
        return notificacoes_enviadas
    
    def _ja_foi_enviada(self, endividamento_id, tipo_notificacao):
        """Verifica se a notificação já foi enviada para este endividamento"""
        return db.session.query(HistoricoNotificacao).filter(
            and_(
                HistoricoNotificacao.endividamento_id == endividamento_id,
                HistoricoNotificacao.tipo_notificacao == tipo_notificacao,
                HistoricoNotificacao.sucesso == True
            )
        ).first() is not None
    
    def _enviar_notificacao(self, endividamento, tipo_notificacao):
        """Envia a notificação por e-mail"""
        try:
            # Buscar configuração de notificação
            notificacao_config = NotificacaoEndividamento.query.filter_by(
                endividamento_id=endividamento.id,
                ativo=True
            ).first()
            
            if not notificacao_config:
                return False
            
            emails = json.loads(notificacao_config.emails)
            if not emails:
                return False
            
            # Preparar dados do e-mail
            assunto, corpo = self._preparar_email(endividamento, tipo_notificacao)
            
            # Enviar e-mail
            sucesso = self.email_service.send_email(
                destinatarios=emails,
                assunto=assunto,
                corpo=corpo,
                html=True
            )
            
            # Registrar no histórico
            self._registrar_historico(
                endividamento.id,
                tipo_notificacao,
                emails,
                sucesso
            )
            
            return sucesso
            
        except Exception as e:
            logger.error(f"Erro ao enviar notificação para endividamento {endividamento.id}: {str(e)}")
            self._registrar_historico(
                endividamento.id,
                tipo_notificacao,
                [],
                False,
                str(e)
            )
            return False
    
    def _preparar_email(self, endividamento, tipo_notificacao):
        """Prepara o assunto e corpo do e-mail"""
        dias = self.INTERVALOS_NOTIFICACAO[tipo_notificacao]
        
        if dias >= 30:
            if dias == 180:
                periodo = "6 meses"
            elif dias == 90:
                periodo = "3 meses"
            else:
                periodo = f"{dias} dias"
        else:
            periodo = f"{dias} dia{'s' if dias > 1 else ''}"
        
        assunto = f"Lembrete: Endividamento vence em {periodo} - {endividamento.banco}"
        
        # Calcular valor total das parcelas pendentes
        valor_total_pendente = sum(
            parcela.valor for parcela in endividamento.parcelas 
            if not parcela.pago
        )
        
        # Preparar lista de pessoas
        pessoas_nomes = [pessoa.nome for pessoa in endividamento.pessoas]
        
        corpo = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #d32f2f; border-bottom: 2px solid #d32f2f; padding-bottom: 10px;">
                    🚨 Lembrete de Vencimento de Endividamento
                </h2>
                
                <p>Este é um lembrete automático sobre um endividamento que vencerá em <strong>{periodo}</strong>.</p>
                
                <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #1976d2;">Detalhes do Endividamento:</h3>
                    <ul style="list-style: none; padding: 0;">
                        <li><strong>Banco:</strong> {endividamento.banco}</li>
                        <li><strong>Número da Proposta:</strong> {endividamento.numero_proposta}</li>
                        <li><strong>Data de Vencimento:</strong> {endividamento.data_vencimento_final.strftime('%d/%m/%Y')}</li>
                        <li><strong>Taxa de Juros:</strong> {endividamento.taxa_juros}% {'a.a.' if endividamento.tipo_taxa_juros == 'ano' else 'a.m.'}</li>
                        {f'<li><strong>Valor da Operação:</strong> R$ {endividamento.valor_operacao:,.2f}</li>' if endividamento.valor_operacao else ''}
                        <li><strong>Valor Total Pendente:</strong> R$ {valor_total_pendente:,.2f}</li>
                        <li><strong>Pessoas Vinculadas:</strong> {', '.join(pessoas_nomes)}</li>
                    </ul>
                </div>
                
                <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p style="margin: 0;"><strong>⚠️ Atenção:</strong> Certifique-se de que todas as providências necessárias foram tomadas para o cumprimento das obrigações dentro do prazo.</p>
                </div>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                
                <p style="font-size: 12px; color: #666;">
                    Este é um e-mail automático do Sistema de Gestão Agrícola. Não responda a este e-mail.
                    <br>Data de envio: {datetime.now().strftime('%d/%m/%Y às %H:%M')}
                </p>
            </div>
        </body>
        </html>
        """
        
        return assunto, corpo
    
    def _registrar_historico(self, endividamento_id, tipo_notificacao, emails, sucesso, erro_mensagem=None):
        """Registra o envio da notificação no histórico"""
        try:
            historico = HistoricoNotificacao(
                endividamento_id=endividamento_id,
                tipo_notificacao=tipo_notificacao,
                emails_enviados=json.dumps(emails),
                sucesso=sucesso,
                erro_mensagem=erro_mensagem
            )
            
            db.session.add(historico)
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Erro ao registrar histórico de notificação: {str(e)}")
            db.session.rollback()
    
    def configurar_notificacao(self, endividamento_id, emails, ativo=True):
        """Configura ou atualiza as notificações para um endividamento"""
        try:
            # Buscar configuração existente
            notificacao = NotificacaoEndividamento.query.filter_by(
                endividamento_id=endividamento_id
            ).first()
            
            if notificacao:
                # Atualizar existente
                notificacao.emails = json.dumps(emails)
                notificacao.ativo = ativo
                notificacao.updated_at = datetime.utcnow()
            else:
                # Criar nova
                notificacao = NotificacaoEndividamento(
                    endividamento_id=endividamento_id,
                    emails=json.dumps(emails),
                    ativo=ativo
                )
                db.session.add(notificacao)
            
            db.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Erro ao configurar notificação: {str(e)}")
            db.session.rollback()
            return False
    
    def obter_configuracao(self, endividamento_id):
        """Obtém a configuração de notificação para um endividamento"""
        notificacao = NotificacaoEndividamento.query.filter_by(
            endividamento_id=endividamento_id
        ).first()
        
        if notificacao:
            return {
                'emails': json.loads(notificacao.emails),
                'ativo': notificacao.ativo
            }
        
        return {'emails': [], 'ativo': False}
    
    def obter_historico(self, endividamento_id):
        """Obtém o histórico de notificações para um endividamento"""
        historicos = HistoricoNotificacao.query.filter_by(
            endividamento_id=endividamento_id
        ).order_by(HistoricoNotificacao.data_envio.desc()).all()
        
        return [historico.to_dict() for historico in historicos]

