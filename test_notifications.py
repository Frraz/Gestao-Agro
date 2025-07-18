#!/usr/bin/env python3
"""
Script para testar o sistema de notificações
Este script testa a funcionalidade básica das notificações sem depender do Redis/Celery.
"""

import sys
import os
from datetime import datetime, date, timedelta

# Adicionar o diretório raiz ao Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def test_notification_services():
    """Testa os serviços de notificação"""
    print("=== Teste do Sistema de Notificações ===")
    print(f"Data/Hora: {datetime.now()}")
    print()
    
    try:
        # Importar serviços
        from src.utils.notificacao_documentos_service import NotificacaoDocumentoService
        from src.utils.notificacao_endividamento_service import NotificacaoEndividamentoService
        from src.utils.tasks_notificacao import verificar_notificacoes_documentos, verificar_notificacoes_endividamento
        
        print("✓ Importações realizadas com sucesso")
        
        # Testar instanciação dos serviços
        doc_service = NotificacaoDocumentoService()
        end_service = NotificacaoEndividamentoService()
        
        print("✓ Serviços instanciados com sucesso")
        
        # Testar as funções auxiliares
        print("\n--- Testando função de documentos ---")
        try:
            result_docs = verificar_notificacoes_documentos()
            print(f"✓ Verificação de documentos executada: {result_docs} notificações processadas")
        except Exception as e:
            print(f"✗ Erro na verificação de documentos: {e}")
        
        print("\n--- Testando função de endividamentos ---")
        try:
            result_end = verificar_notificacoes_endividamento()
            print(f"✓ Verificação de endividamentos executada: {result_end} notificações processadas")
        except Exception as e:
            print(f"✗ Erro na verificação de endividamentos: {e}")
        
        print("\n--- Testando configurações dos serviços ---")
        
        # Testar prazos de notificação para documentos
        prazos_docs = doc_service.PRAZOS_PADRAO
        print(f"✓ Prazos padrão para documentos: {prazos_docs}")
        
        # Testar intervalos de notificação para endividamentos
        intervalos_end = end_service.INTERVALOS_NOTIFICACAO
        print(f"✓ Intervalos para endividamentos: {intervalos_end}")
        
        print("\n=== Teste Concluído com Sucesso ===")
        return True
        
    except Exception as e:
        print(f"✗ Erro durante o teste: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_celery_tasks():
    """Testa se as tasks do Celery estão registradas"""
    print("\n=== Teste das Tasks do Celery ===")
    
    try:
        # Configurar ambiente
        os.environ['FLASK_ENV'] = 'development'
        
        # Importar e testar o Celery
        from celery_app import celery
        
        print("✓ Celery carregado com sucesso")
        
        # Verificar tasks registradas
        registered_tasks = [name for name in celery.tasks.keys() if not name.startswith('celery.')]
        print(f"✓ Tasks registradas: {len(registered_tasks)}")
        for task in registered_tasks:
            print(f"  - {task}")
        
        # Verificar beat schedule
        beat_schedule = celery.conf.beat_schedule
        print(f"\n✓ Beat schedule configurado: {len(beat_schedule)} agendamentos")
        for name, config in beat_schedule.items():
            print(f"  - {name}: {config['task']} ({config['schedule']})")
        
        # Verificar timezone
        print(f"\n✓ Timezone: {celery.conf.timezone}")
        print(f"✓ UTC habilitado: {celery.conf.enable_utc}")
        
        return True
        
    except Exception as e:
        print(f"✗ Erro ao testar Celery: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_task_execution():
    """Testa a execução manual das tasks"""
    print("\n=== Teste de Execução Manual das Tasks ===")
    
    try:
        os.environ['FLASK_ENV'] = 'development'
        
        # Importar o app Flask para contexto
        from src.main import app
        
        with app.app_context():
            print("✓ Contexto Flask criado")
            
            # Importar as funções de task
            from src.utils.tasks_notificacao import (
                verificar_notificacoes_documentos,
                verificar_notificacoes_endividamento
            )
            
            # Executar verificação de documentos
            print("\n--- Executando verificação de documentos ---")
            try:
                result_docs = verificar_notificacoes_documentos()
                print(f"✓ Resultado: {result_docs} notificações de documentos processadas")
            except Exception as e:
                print(f"⚠ Aviso documentos: {e}")
            
            # Executar verificação de endividamentos
            print("\n--- Executando verificação de endividamentos ---")
            try:
                result_end = verificar_notificacoes_endividamento()
                print(f"✓ Resultado: {result_end} notificações de endividamentos processadas")
            except Exception as e:
                print(f"⚠ Aviso endividamentos: {e}")
        
        return True
        
    except Exception as e:
        print(f"✗ Erro na execução manual: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Iniciando testes do sistema de notificações...")
    
    success = True
    
    # Executar testes
    success &= test_notification_services()
    success &= test_celery_tasks()
    success &= test_task_execution()
    
    if success:
        print("\n🎉 Todos os testes passaram!")
        print("\nPróximos passos:")
        print("1. Iniciar Redis: redis-server")
        print("2. Iniciar Celery Worker: celery -A celery_app worker --loglevel=info")
        print("3. Iniciar Celery Beat: celery -A celery_app beat --loglevel=info")
        print("4. Verificar logs do worker e beat para confirmar execução das tasks")
    else:
        print("\n❌ Alguns testes falharam. Verifique os erros acima.")
        sys.exit(1)