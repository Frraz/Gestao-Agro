#!/usr/bin/env python

"""Verifica quais tabelas existem no banco"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main import app
from src.models.db import db
from sqlalchemy import inspect

with app.app_context():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    
    print("Tabelas existentes no banco:")
    for table in sorted(tables):
        print(f"  - {table}")
    
    print("\nVerificando tabelas de notificação:")
    if 'notificacao_endividamento' in tables:
        print("✅ notificacao_endividamento existe")
    else:
        print("❌ notificacao_endividamento NÃO existe")
        
    if 'historico_notificacao' in tables:
        print("✅ historico_notificacao existe")
    else:
        print("❌ historico_notificacao NÃO existe")