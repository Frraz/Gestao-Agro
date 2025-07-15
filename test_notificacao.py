#!/usr/bin/env python
"""Script para testar o sistema de notificações manualmente"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main import app
from datetime import datetime, date, timedelta

def test_notifications():
    with app.app_context():
        print("=== TESTE DO SISTEMA DE NOTIFICAÇÕES ===")
        print(f"Horário: {datetime.now()}")
        print("-" * 50)
        
        # Teste 1: Verificar configurações
        print("\n1. Verificando configurações:")
        print(f"   Redis URL: {app.config.get('REDIS_URL', 'NÃO CONFIGURADO')}")
        print(f"   Celery Broker: {app.config.get('CELERY_BROKER_URL', 'NÃO CONFIGURADO')}")
        print(f"   Email Server: {app.config.get('MAIL_SERVER', 'NÃO CONFIGURADO')}")
        
        # Teste 2: Contar notificações pendentes
        print("\n2. Contando entidades com notificações:")
        try:
            from src.models.notificacao_endividamento import NotificacaoEndividamento
            from src.models.endividamento import Endividamento
            from src.models.documento import Documento
            
            notif_ativas = NotificacaoEndividamento.query.filter_by(ativo=True).count()
            endividamentos_proximos = Endividamento.query.filter(
                Endividamento.data_vencimento_final.between(date.today(), date.today() + timedelta(days=180))
            ).count()
            docs_proximos = Documento.query.filter(
                Documento.data_vencimento.between(date.today(), date.today() + timedelta(days=90))
            ).count()
            
            print(f"   Notificações de endividamento ativas: {notif_ativas}")
            print(f"   Endividamentos vencendo em 180 dias: {endividamentos_proximos}")
            print(f"   Documentos vencendo em 90 dias: {docs_proximos}")
        except Exception as e:
            print(f"   ERRO: {e}")
        
        # Teste 3: Executar verificação manual
        print("\n3. Executando verificação manual de notificações:")
        try:
            from src.utils.notificacao_endividamento_service import NotificacaoEndividamentoService
            from src.utils.notificacao_documentos_service import NotificacaoDocumentoService
            
            # Endividamentos
            print("   - Verificando endividamentos...")
            service_end = NotificacaoEndividamentoService()
            count_end = service_end.verificar_e_enviar_notificacoes()
            print(f"     Notificações de endividamento enviadas: {count_end}")
            
            # Documentos
            print("   - Verificando documentos...")
            service_doc = NotificacaoDocumentoService()
            count_doc = service_doc.verificar_e_enviar_notificacoes()
            print(f"     Notificações de documentos enviadas: {count_doc}")
            
            print(f"\n   TOTAL DE NOTIFICAÇÕES ENVIADAS: {count_end + count_doc}")
            
        except Exception as e:
            print(f"   ERRO ao executar verificação: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "=" * 50)
        print("TESTE CONCLUÍDO")

if __name__ == "__main__":
    test_notifications()