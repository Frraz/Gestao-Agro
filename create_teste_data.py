#create_teste_data.py

#!/usr/bin/env python
"""Cria dados de teste para notificações - versão final corrigida"""
import os
import sys
from datetime import date, timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main import app
from src.models.db import db
from src.models.endividamento import Endividamento
from src.models.documento import Documento, TipoDocumento, TipoEntidade
from src.models.notificacao_endividamento import NotificacaoEndividamento
from src.models.pessoa import Pessoa

def create_test_data():
    with app.app_context():
        print("=== Criando dados de teste para notificações ===")
        
        # Obter uma pessoa existente
        pessoa = Pessoa.query.first()
        if pessoa:
            print(f"✅ Usando pessoa existente: {pessoa.nome}")
        
        # Criar documentos com tipos válidos e data_emissao
        # 1. Criar documento vencendo em 7 dias
        doc_7_dias = Documento.query.filter_by(nome="Certidão Ambiental - URGENTE").first()
        if not doc_7_dias:
            doc_7_dias = Documento(
                nome="Certidão Ambiental - URGENTE",
                tipo=TipoDocumento.CERTIDOES,
                data_emissao=date.today() - timedelta(days=30),  # Emitido há 30 dias
                data_vencimento=date.today() + timedelta(days=7),
                tipo_entidade=TipoEntidade.PESSOA if pessoa else None,
                pessoa_id=pessoa.id if pessoa else None
            )
            db.session.add(doc_7_dias)
            db.session.commit()
            print(f"✅ Criado documento vencendo em {doc_7_dias.data_vencimento}")
        
        # 2. Criar documento vencendo em 30 dias
        doc_30_dias = Documento.query.filter_by(nome="Contrato de Arrendamento - 30 Dias").first()
        if not doc_30_dias:
            doc_30_dias = Documento(
                nome="Contrato de Arrendamento - 30 Dias",
                tipo=TipoDocumento.CONTRATOS,
                data_emissao=date.today() - timedelta(days=60),  # Emitido há 60 dias
                data_vencimento=date.today() + timedelta(days=30),
                tipo_entidade=TipoEntidade.PESSOA if pessoa else None,
                pessoa_id=pessoa.id if pessoa else None
            )
            db.session.add(doc_30_dias)
            db.session.commit()
            print(f"✅ Criado documento vencendo em {doc_30_dias.data_vencimento}")
        
        # 3. Criar documento vencendo em 60 dias
        doc_60_dias = Documento.query.filter_by(nome="Matrícula do Imóvel - 60 Dias").first()
        if not doc_60_dias:
            doc_60_dias = Documento(
                nome="Matrícula do Imóvel - 60 Dias",
                tipo=TipoDocumento.DOCUMENTOS_AREA,
                data_emissao=date.today() - timedelta(days=90),  # Emitido há 90 dias
                data_vencimento=date.today() + timedelta(days=60),
                tipo_entidade=TipoEntidade.PESSOA if pessoa else None,
                pessoa_id=pessoa.id if pessoa else None
            )
            db.session.add(doc_60_dias)
            db.session.commit()
            print(f"✅ Criado documento vencendo em {doc_60_dias.data_vencimento}")
        
        # 4. Criar documento vencendo em 90 dias
        doc_90_dias = Documento.query.filter_by(nome="Alvará de Funcionamento - 90 Dias").first()
        if not doc_90_dias:
            doc_90_dias = Documento(
                nome="Alvará de Funcionamento - 90 Dias",
                tipo=TipoDocumento.OUTROS,
                tipo_personalizado="Alvará Municipal",
                data_emissao=date.today() - timedelta(days=275),  # Emitido há 275 dias
                data_vencimento=date.today() + timedelta(days=90),
                tipo_entidade=TipoEntidade.PESSOA if pessoa else None,
                pessoa_id=pessoa.id if pessoa else None
            )
            db.session.add(doc_90_dias)
            db.session.commit()
            print(f"✅ Criado documento vencendo em {doc_90_dias.data_vencimento}")
        
        # Contar totais
        print("\n📊 Resumo dos dados criados:")
        print("=" * 50)
        
        # Endividamentos
        total_end = Endividamento.query.filter(
            Endividamento.data_vencimento_final.between(
                date.today(), 
                date.today() + timedelta(days=180)
            )
        ).count()
        
        # Documentos
        total_doc = Documento.query.filter(
            Documento.data_vencimento != None,
            Documento.data_vencimento.between(
                date.today(),
                date.today() + timedelta(days=90)
            )
        ).count()
        
        # Notificações ativas
        total_notif = NotificacaoEndividamento.query.filter_by(ativo=True).count()
        
        print(f"   - Endividamentos próximos do vencimento (180 dias): {total_end}")
        print(f"   - Documentos próximos do vencimento (90 dias): {total_doc}")
        print(f"   - Notificações de endividamento ativas: {total_notif}")
        
        # Detalhar vencimentos urgentes
        print("\n🚨 Vencimentos URGENTES (próximos 30 dias):")
        
        # Endividamentos urgentes
        ends_urgentes = Endividamento.query.filter(
            Endividamento.data_vencimento_final.between(
                date.today(), 
                date.today() + timedelta(days=30)
            )
        ).all()
        
        for end in ends_urgentes:
            dias = (end.data_vencimento_final - date.today()).days
            notif = NotificacaoEndividamento.query.filter_by(
                endividamento_id=end.id,
                ativo=True
            ).first()
            emails = "SIM" if notif else "NÃO"
            print(f"   - Endividamento {end.numero_proposta}: vence em {dias} dias - Notificação: {emails}")
        
        # Documentos urgentes
        docs_urgentes = Documento.query.filter(
            Documento.data_vencimento != None,
            Documento.data_vencimento.between(
                date.today(),
                date.today() + timedelta(days=30)
            )
        ).all()
        
        for doc in docs_urgentes:
            dias = (doc.data_vencimento - date.today()).days
            print(f"   - Documento '{doc.nome}': vence em {dias} dias")
        
        print("\n✅ Dados de teste criados com sucesso!")
        print("🔔 Execute 'python test_notificacao.py' para testar as notificações")

if __name__ == "__main__":
    create_test_data()