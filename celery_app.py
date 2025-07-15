# /celery_app.py

"""
Arquivo de entrada para o Celery Worker e Beat
"""
import os
import sys

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.main import celery  # Importa APENAS o celery, não a app

if __name__ == '__main__':
    celery.start()