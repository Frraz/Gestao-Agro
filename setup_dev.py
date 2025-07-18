#!/usr/bin/env python3
"""
Script para inicialização rápida do banco de dados em desenvolvimento
"""

import sys
import os

# Adicionar o diretório raiz ao Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def init_database():
    """Inicializa o banco de dados"""
    print("🗄️ Inicializando banco de dados...")
    
    try:
        # Configurar ambiente
        os.environ['FLASK_ENV'] = 'development'
        
        # Importar app e db
        from src.main import app, db
        
        with app.app_context():
            print("✓ Contexto Flask criado")
            
            # Criar todas as tabelas
            db.create_all()
            print("✓ Tabelas criadas")
            
            # Verificar se as tabelas foram criadas
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            print(f"✓ {len(tables)} tabelas encontradas:")
            for table in sorted(tables):
                print(f"  - {table}")
            
            # Verificar tabelas específicas de notificação
            notification_tables = [
                'notificacao_endividamento',
                'historico_notificacao'
            ]
            
            missing_tables = [t for t in notification_tables if t not in tables]
            if missing_tables:
                print(f"⚠️  Tabelas de notificação faltando: {missing_tables}")
                print("   Execute as migrações: flask db upgrade")
            else:
                print("✅ Todas as tabelas de notificação estão presentes")
            
        return True
        
    except Exception as e:
        print(f"❌ Erro ao inicializar banco: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_sample_data():
    """Cria dados de exemplo para testar notificações"""
    print("\n📝 Criando dados de exemplo...")
    
    try:
        from src.main import app, db
        from datetime import date, timedelta
        
        with app.app_context():
            # Exemplo: Criar uma pessoa
            try:
                from src.models.pessoa import Pessoa
                pessoa = Pessoa.query.first()
                if not pessoa:
                    pessoa = Pessoa(
                        nome="João da Silva",
                        cpf_cnpj="12345678901",
                        email="teste@example.com",
                        telefone="(11) 99999-9999"
                    )
                    db.session.add(pessoa)
                    db.session.commit()
                    print("✓ Pessoa de exemplo criada")
                else:
                    print("✓ Pessoa já existe")
            except Exception as e:
                print(f"⚠️  Erro ao criar pessoa: {e}")
            
            # Exemplo: Criar um documento com vencimento próximo
            try:
                from src.models.documento import Documento, TipoDocumento
                
                doc = Documento.query.first()
                if not doc:
                    doc = Documento(
                        nome="Licença Ambiental de Teste",
                        tipo=TipoDocumento.LICENCA,
                        data_emissao=date.today() - timedelta(days=30),
                        data_vencimento=date.today() + timedelta(days=7),  # Vence em 7 dias
                        pessoa_id=pessoa.id if pessoa else None,
                        emails_notificacao='["teste@example.com"]'
                    )
                    db.session.add(doc)
                    db.session.commit()
                    print("✓ Documento de exemplo criado (vence em 7 dias)")
                else:
                    print("✓ Documento já existe")
            except Exception as e:
                print(f"⚠️  Erro ao criar documento: {e}")
            
        return True
        
    except Exception as e:
        print(f"❌ Erro ao criar dados de exemplo: {e}")
        return False

def test_notification_system():
    """Testa o sistema de notificações com dados reais"""
    print("\n🧪 Testando sistema de notificações...")
    
    try:
        from src.main import app
        from src.utils.tasks_notificacao import verificar_notificacoes_documentos, verificar_notificacoes_endividamento
        
        with app.app_context():
            # Testar notificações de documentos
            result_docs = verificar_notificacoes_documentos()
            print(f"✓ Documentos processados: {result_docs} notificações")
            
            # Testar notificações de endividamentos
            result_end = verificar_notificacoes_endividamento()
            print(f"✓ Endividamentos processados: {result_end} notificações")
            
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return False

def main():
    """Função principal"""
    print("🚀 Setup de Desenvolvimento - Sistema de Notificações")
    print("=" * 60)
    
    success = True
    
    # 1. Inicializar banco
    success &= init_database()
    
    # 2. Criar dados de exemplo
    success &= create_sample_data()
    
    # 3. Testar sistema
    success &= test_notification_system()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Setup concluído com sucesso!")
        print("\nPróximos passos:")
        print("1. Configurar Redis: redis-server")
        print("2. Iniciar worker: celery -A celery_app worker --loglevel=info")
        print("3. Iniciar beat: celery -A celery_app beat --loglevel=info")
        print("4. Testar: python celery_diagnostic.py")
    else:
        print("❌ Alguns problemas foram encontrados.")
        print("Verifique os erros acima.")

if __name__ == "__main__":
    main()