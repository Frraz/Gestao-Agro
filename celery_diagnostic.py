#!/usr/bin/env python3
"""
Script para testar e verificar o funcionamento do sistema de notificações
com workers Celery simulados.
"""

import sys
import os
from datetime import datetime, date, timedelta

# Adicionar o diretório raiz ao Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def test_worker_simulation():
    """Simula a execução das tasks como se fossem executadas pelo worker"""
    print("\n=== Simulação de Execução do Worker Celery ===")
    
    try:
        # Configurar ambiente
        os.environ['FLASK_ENV'] = 'development'
        
        # Importar o app Flask
        from src.main import app, celery
        
        print("✓ App Flask e Celery carregados")
        
        # Testar tasks individualmente
        with app.app_context():
            print("✓ Contexto Flask ativo")
            
            # Listar todas as tasks registradas
            registered_tasks = [name for name in celery.tasks.keys() if not name.startswith('celery.')]
            print(f"\n📋 Tasks registradas ({len(registered_tasks)}):")
            for task_name in registered_tasks:
                print(f"  - {task_name}")
            
            # Tentar executar as principais tasks
            print("\n🔄 Testando execução das tasks principais:")
            
            # 1. Testar task de documentos
            try:
                task_doc = celery.tasks.get('tasks.processar_notificacoes_documentos')
                if task_doc:
                    print("\n--- Executando task de documentos ---")
                    result = task_doc.apply().get()
                    print(f"✓ Task documentos executada: {result}")
                else:
                    print("⚠ Task de documentos não encontrada")
            except Exception as e:
                print(f"✗ Erro na task de documentos: {e}")
            
            # 2. Testar task de endividamentos
            try:
                task_end = celery.tasks.get('tasks.processar_notificacoes_endividamento')
                if task_end:
                    print("\n--- Executando task de endividamentos ---")
                    result = task_end.apply().get()
                    print(f"✓ Task endividamentos executada: {result}")
                else:
                    print("⚠ Task de endividamentos não encontrada")
            except Exception as e:
                print(f"✗ Erro na task de endividamentos: {e}")
            
            # 3. Testar task geral
            try:
                task_all = celery.tasks.get('tasks.processar_todas_notificacoes')
                if task_all:
                    print("\n--- Executando task de todas as notificações ---")
                    result = task_all.apply().get()
                    print(f"✓ Task geral executada: {result}")
                else:
                    print("⚠ Task geral não encontrada")
            except Exception as e:
                print(f"✗ Erro na task geral: {e}")
            
            # 4. Testar task de teste
            try:
                task_test = celery.tasks.get('tasks.test_notificacoes')
                if task_test:
                    print("\n--- Executando task de teste ---")
                    result = task_test.apply().get()
                    print(f"✓ Task de teste executada: {result}")
                else:
                    print("⚠ Task de teste não encontrada")
            except Exception as e:
                print(f"✗ Erro na task de teste: {e}")
        
        return True
        
    except Exception as e:
        print(f"✗ Erro na simulação do worker: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_beat_schedule_validation():
    """Valida se a configuração do beat está correta"""
    print("\n=== Validação da Configuração do Beat ===")
    
    try:
        from celery_app import celery
        
        beat_schedule = celery.conf.beat_schedule
        registered_tasks = [name for name in celery.tasks.keys() if not name.startswith('celery.')]
        
        print(f"📅 Agendamentos configurados: {len(beat_schedule)}")
        
        validation_errors = []
        
        for schedule_name, config in beat_schedule.items():
            task_name = config['task']
            schedule = config['schedule']
            
            print(f"\n🔍 Validando agendamento: {schedule_name}")
            print(f"   Task: {task_name}")
            print(f"   Schedule: {schedule}")
            
            # Verificar se a task existe
            if task_name in registered_tasks:
                print("   ✓ Task encontrada")
            else:
                print("   ✗ Task NÃO encontrada")
                validation_errors.append(f"Task '{task_name}' não está registrada")
            
            # Verificar se a task pode ser executada
            try:
                task = celery.tasks.get(task_name)
                if task:
                    print("   ✓ Task pode ser chamada")
                else:
                    print("   ✗ Task não pode ser obtida")
                    validation_errors.append(f"Task '{task_name}' não pode ser obtida")
            except Exception as e:
                print(f"   ✗ Erro ao obter task: {e}")
                validation_errors.append(f"Erro ao obter task '{task_name}': {e}")
        
        if validation_errors:
            print(f"\n❌ Encontrados {len(validation_errors)} erros de validação:")
            for error in validation_errors:
                print(f"   - {error}")
            return False
        else:
            print("\n✅ Todas as validações passaram!")
            return True
            
    except Exception as e:
        print(f"✗ Erro na validação do beat: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_celery_commands():
    """Mostra os comandos para executar o Celery em produção"""
    print("\n=== Comandos para Execução em Produção ===")
    
    print("\n📦 Pré-requisitos:")
    print("1. Redis deve estar rodando:")
    print("   sudo apt-get install redis-server")
    print("   redis-server")
    print("")
    print("2. Instalar dependências:")
    print("   pip install -r requirements.txt")
    
    print("\n🚀 Comandos para iniciar o sistema:")
    print("")
    print("1. Worker Celery (em um terminal):")
    print("   cd /path/to/project")
    print("   celery -A celery_app worker --loglevel=info")
    print("")
    print("2. Scheduler Celery Beat (em outro terminal):")
    print("   cd /path/to/project")
    print("   celery -A celery_app beat --loglevel=info")
    print("")
    print("3. Monitor Celery (opcional, em outro terminal):")
    print("   celery -A celery_app flower")
    print("")
    print("4. Aplicação Flask (em outro terminal):")
    print("   cd /path/to/project")
    print("   python src/main.py")
    
    print("\n📊 Comandos de monitoramento:")
    print("")
    print("Ver status dos workers:")
    print("   celery -A celery_app status")
    print("")
    print("Ver tasks ativas:")
    print("   celery -A celery_app inspect active")
    print("")
    print("Ver agendamentos:")
    print("   celery -A celery_app inspect scheduled")
    print("")
    print("Executar task manualmente:")
    print("   celery -A celery_app call tasks.processar_todas_notificacoes")
    
    print("\n🔧 Variáveis de ambiente necessárias (.env):")
    print("   REDIS_URL=redis://localhost:6379/0")
    print("   CELERY_BROKER_URL=redis://localhost:6379/0")
    print("   CELERY_RESULT_BACKEND=redis://localhost:6379/0")
    print("   MAIL_SERVER=smtp.gmail.com")
    print("   MAIL_USERNAME=seu_email@gmail.com")
    print("   MAIL_PASSWORD=sua_senha_app")
    print("   MAIL_DEFAULT_SENDER=seu_email@gmail.com")

def run_diagnostic():
    """Executa diagnóstico completo do sistema"""
    print("🔧 DIAGNÓSTICO DO SISTEMA DE NOTIFICAÇÕES")
    print("=" * 60)
    print(f"Data/Hora: {datetime.now()}")
    print(f"Python: {sys.version}")
    print("")
    
    success = True
    
    # Teste básico de importações
    print("1️⃣ Testando importações...")
    try:
        from src.utils.notificacao_documentos_service import NotificacaoDocumentoService
        from src.utils.notificacao_endividamento_service import NotificacaoEndividamentoService
        print("   ✓ Serviços de notificação importados")
    except Exception as e:
        print(f"   ✗ Erro nas importações: {e}")
        success = False
    
    # Teste do Celery
    print("\n2️⃣ Testando configuração do Celery...")
    try:
        from celery_app import celery
        print(f"   ✓ Celery carregado")
        print(f"   ✓ Broker: {celery.conf.broker_url}")
        print(f"   ✓ Timezone: {celery.conf.timezone}")
        print(f"   ✓ Tasks registradas: {len([t for t in celery.tasks.keys() if not t.startswith('celery.')])}")
    except Exception as e:
        print(f"   ✗ Erro no Celery: {e}")
        success = False
    
    # Teste de simulação
    print("\n3️⃣ Testando simulação de worker...")
    success &= test_worker_simulation()
    
    # Validação do beat
    print("\n4️⃣ Validando configuração do beat...")
    success &= test_beat_schedule_validation()
    
    # Mostrar comandos
    show_celery_commands()
    
    # Resultado final
    print("\n" + "=" * 60)
    if success:
        print("🎉 DIAGNÓSTICO CONCLUÍDO COM SUCESSO!")
        print("\nO sistema está configurado corretamente.")
        print("Para colocar em produção, siga os comandos mostrados acima.")
    else:
        print("❌ DIAGNÓSTICO ENCONTROU PROBLEMAS!")
        print("\nVerifique os erros acima antes de colocar em produção.")
    
    print("\n💡 Dica: Execute este script sempre que fizer alterações no sistema de notificações.")
    
    return success

if __name__ == "__main__":
    run_diagnostic()