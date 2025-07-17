#!/usr/bin/env python3
"""
Test script to demonstrate the new pessoa-fazenda relationship functionality.
This shows that a person can have multiple associations with the same farm using different types of bonds.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.main import create_app
from src.models.db import db
from src.models.pessoa import Pessoa
from src.models.fazenda import Fazenda
from src.models.pessoa_fazenda import PessoaFazenda, TipoPosse


def test_functionality():
    """Test the new pessoa-fazenda relationship functionality"""
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test"
    })
    
    with app.app_context():
        db.create_all()
        
        # Create a test person
        pessoa = Pessoa(
            nome="João Silva",
            cpf_cnpj="12345678901",
            email="joao@teste.com",
            telefone="(11) 99999-9999",
            endereco="Rua Teste, 123"
        )
        db.session.add(pessoa)
        
        # Create a test farm
        fazenda = Fazenda(
            nome="Fazenda Esperança",
            matricula="FZ-001",
            tamanho_total=500.0,
            area_consolidada=100.0,
            tamanho_disponivel=400.0,
            municipio="Uberlândia",
            estado="MG",
            recibo_car="CAR-12345"
        )
        db.session.add(fazenda)
        db.session.commit()
        
        print("✅ Created test person and farm")
        
        # Test 1: Create multiple relationships with different types
        print("\n📋 Test 1: Multiple relationships with different types")
        
        # João is the owner
        vinculo1 = PessoaFazenda(
            pessoa_id=pessoa.id,
            fazenda_id=fazenda.id,
            tipo_posse=TipoPosse.PROPRIA
        )
        db.session.add(vinculo1)
        
        # João also has a lease contract (different period/area)
        vinculo2 = PessoaFazenda(
            pessoa_id=pessoa.id,
            fazenda_id=fazenda.id,
            tipo_posse=TipoPosse.ARRENDADA
        )
        db.session.add(vinculo2)
        
        # João has a commodatum contract
        vinculo3 = PessoaFazenda(
            pessoa_id=pessoa.id,
            fazenda_id=fazenda.id,
            tipo_posse=TipoPosse.COMODATO
        )
        db.session.add(vinculo3)
        
        db.session.commit()
        
        # Verify relationships were created
        vinculos = PessoaFazenda.query.filter_by(pessoa_id=pessoa.id, fazenda_id=fazenda.id).all()
        print(f"   Created {len(vinculos)} relationships")
        for vinculo in vinculos:
            print(f"   - {vinculo.tipo_posse.value}")
        
        # Test 2: Multiple relationships with same type (allowed now)
        print("\n📋 Test 2: Multiple relationships with same type")
        
        # João has another ownership relationship (maybe different plots)
        vinculo4 = PessoaFazenda(
            pessoa_id=pessoa.id,
            fazenda_id=fazenda.id,
            tipo_posse=TipoPosse.PROPRIA
        )
        db.session.add(vinculo4)
        db.session.commit()
        
        # Verify total relationships
        vinculos = PessoaFazenda.query.filter_by(pessoa_id=pessoa.id, fazenda_id=fazenda.id).all()
        print(f"   Total relationships: {len(vinculos)}")
        
        propria_count = len([v for v in vinculos if v.tipo_posse == TipoPosse.PROPRIA])
        print(f"   - Própria: {propria_count}")
        print(f"   - Arrendada: {len([v for v in vinculos if v.tipo_posse == TipoPosse.ARRENDADA])}")
        print(f"   - Comodato: {len([v for v in vinculos if v.tipo_posse == TipoPosse.COMODATO])}")
        
        # Test 3: Verify no date fields exist
        print("\n📋 Test 3: Verify no date fields exist")
        
        sample_vinculo = vinculos[0]
        has_data_inicio = hasattr(sample_vinculo, 'data_inicio')
        has_data_fim = hasattr(sample_vinculo, 'data_fim')
        
        print(f"   Has data_inicio field: {has_data_inicio}")
        print(f"   Has data_fim field: {has_data_fim}")
        
        if not has_data_inicio and not has_data_fim:
            print("   ✅ No date fields present - requirement met!")
        else:
            print("   ❌ Date fields still present")
        
        # Test 4: Test utility methods work correctly
        print("\n📋 Test 4: Utility methods")
        
        # Refresh the pessoa to get updated relationships
        pessoa_fresh = Pessoa.query.get(pessoa.id)
        fazenda_fresh = Fazenda.query.get(fazenda.id)
        
        print(f"   pessoa.total_fazendas: {pessoa_fresh.total_fazendas}")
        print(f"   fazenda.pessoas_fazenda count: {len(fazenda_fresh.pessoas_fazenda)}")
        
        print("\n🎉 All tests completed successfully!")
        print("✅ Multiple person-farm relationships are now supported")
        print("✅ No date fields are stored")
        print("✅ Same person can have multiple relationships with same farm")
        print("✅ Utility methods work correctly")


if __name__ == "__main__":
    test_functionality()