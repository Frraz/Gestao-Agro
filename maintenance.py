# Script para executar tarefas de manutenção e otimização
import os
import sys
import schedule
import time
import logging
from datetime import datetime

# Adicionar o diretório pai ao PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.main import create_app
from src.utils.tasks_notificacao import processar_notificacoes_endividamento
from src.utils.performance import PerformanceOptimizer
from src.utils.cache import cache

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/maintenance.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def executar_notificacoes():
    """Executa o processamento de notificações"""
    try:
        app = create_app()
        with app.app_context():
            notificacoes_enviadas = processar_notificacoes_endividamento()
            logger.info(f"Processamento de notificações concluído. {notificacoes_enviadas} notificações enviadas.")
    except Exception as e:
        logger.error(f"Erro ao executar notificações: {e}")

def limpar_cache():
    """Limpa cache antigo"""
    try:
        app = create_app()
        with app.app_context():
            # Limpar cache de dashboard (atualizar a cada hora)
            cache.clear_pattern('dashboard:*')
            logger.info("Cache de dashboard limpo com sucesso")
    except Exception as e:
        logger.error(f"Erro ao limpar cache: {e}")

def otimizar_banco():
    """Executa otimizações no banco de dados"""
    try:
        app = create_app()
        with app.app_context():
            optimizer = PerformanceOptimizer()
            optimizer.optimize_database_queries()
            logger.info("Otimizações de banco executadas com sucesso")
    except Exception as e:
        logger.error(f"Erro ao otimizar banco: {e}")

def backup_logs():
    """Faz backup dos logs antigos"""
    try:
        import shutil
        from datetime import datetime
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Criar diretório de backup se não existir
        backup_dir = 'logs/backup'
        os.makedirs(backup_dir, exist_ok=True)
        
        # Fazer backup dos logs principais
        log_files = ['logs/sistema_fazendas.log', 'logs/maintenance.log']
        
        for log_file in log_files:
            if os.path.exists(log_file):
                backup_name = f"{backup_dir}/{os.path.basename(log_file)}.{timestamp}"
                shutil.copy2(log_file, backup_name)
                
                # Limpar o log original
                with open(log_file, 'w') as f:
                    f.write('')
                
                logger.info(f"Backup do log {log_file} criado: {backup_name}")
        
    except Exception as e:
        logger.error(f"Erro ao fazer backup dos logs: {e}")

def agendar_tarefas():
    """Agenda todas as tarefas de manutenção"""
    
    # Notificações - executar a cada hora
    schedule.every().hour.do(executar_notificacoes)
    
    # Limpeza de cache - executar a cada 2 horas
    schedule.every(2).hours.do(limpar_cache)
    
    # Otimização de banco - executar diariamente às 2:00
    schedule.every().day.at("02:00").do(otimizar_banco)
    
    # Backup de logs - executar semanalmente aos domingos às 3:00
    schedule.every().sunday.at("03:00").do(backup_logs)
    
    logger.info("Tarefas de manutenção agendadas:")
    logger.info("- Notificações: a cada hora")
    logger.info("- Limpeza de cache: a cada 2 horas")
    logger.info("- Otimização de banco: diariamente às 2:00")
    logger.info("- Backup de logs: semanalmente aos domingos às 3:00")

def executar_scheduler():
    """Executa o scheduler de tarefas"""
    agendar_tarefas()
    
    logger.info("Scheduler de manutenção iniciado")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Verificar a cada minuto
    except KeyboardInterrupt:
        logger.info("Scheduler interrompido pelo usuário")
    except Exception as e:
        logger.error(f"Erro no scheduler: {e}")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Sistema de manutenção e tarefas agendadas')
    parser.add_argument('--task', choices=['notificacoes', 'cache', 'banco', 'backup', 'scheduler'], 
                       help='Executar uma tarefa específica')
    
    args = parser.parse_args()
    
    if args.task == 'notificacoes':
        executar_notificacoes()
    elif args.task == 'cache':
        limpar_cache()
    elif args.task == 'banco':
        otimizar_banco()
    elif args.task == 'backup':
        backup_logs()
    elif args.task == 'scheduler':
        executar_scheduler()
    else:
        print("Uso: python maintenance.py --task [notificacoes|cache|banco|backup|scheduler]")
        print("Ou execute sem argumentos para ver as opções disponíveis")
        
        print("\nTarefas disponíveis:")
        print("- notificacoes: Processar notificações de endividamento")
        print("- cache: Limpar cache do sistema")
        print("- banco: Otimizar banco de dados")
        print("- backup: Fazer backup dos logs")
        print("- scheduler: Executar scheduler de tarefas automáticas")

