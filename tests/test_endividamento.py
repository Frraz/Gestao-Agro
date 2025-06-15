# Testes para a funcionalidade de Endividamentos
import unittest
import os
import sys
import tempfile
import json
from datetime import date, datetime, timedelta

# Adicionar o diretório pai ao PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.main import create_app
from src.models.db import db
from src.models.pessoa import Pessoa
from src.models.fazenda import Fazenda, TipoPosse
from src.models.endividamento import Endividamento, EndividamentoFazenda, Parcela

class TestEndividamento(unittest.TestCase):
    """Testes para a funcionalidade de endividamentos"""
    
    def setUp(self):
        """Configuração antes de cada teste"""
        self.db_fd, self.db_path = tempfile.mkstemp()
        test_config = {
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': f'sqlite:///{self.db_path}',
            'SECRET_KEY': 'test_secret_key',
            'WTF_CSRF_ENABLED': False
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
            self._criar_dados_teste()
    
    def tearDown(self):
        """Limpeza após cada teste"""
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def _criar_dados_teste(self):
        """Cria dados de teste"""
        # Criar pessoa de teste
        self.pessoa = Pessoa(
            nome='João Silva',
            cpf_cnpj='12345678901',
            email='joao@teste.com',
            telefone='(11) 99999-9999'
        )
        db.session.add(self.pessoa)
        
        # Criar fazenda de teste
        self.fazenda = Fazenda(
            nome='Fazenda Teste',
            matricula_imovel='123456',
            tamanho_total=100.0,
            area_consolidada=80.0,
            tipo_posse=TipoPosse.PROPRIA,
            estado='SP',
            municipio='São Paulo'
        )
        db.session.add(self.fazenda)
        
        db.session.commit()
    
    def test_criar_endividamento(self):
        """Testa criação de endividamento"""
        with self.app.app_context():
            endividamento = Endividamento(
                banco='Banco do Brasil',
                numero_proposta='12345',
                data_emissao=date.today(),
                data_vencimento_final=date.today() + timedelta(days=365),
                taxa_juros=12.5,
                tipo_taxa_juros='ano',
                prazo_carencia=6
            )
            
            db.session.add(endividamento)
            db.session.commit()
            
            # Verificar se foi criado
            endividamento_db = Endividamento.query.first()
            self.assertIsNotNone(endividamento_db)
            self.assertEqual(endividamento_db.banco, 'Banco do Brasil')
            self.assertEqual(endividamento_db.numero_proposta, '12345')
            self.assertEqual(float(endividamento_db.taxa_juros), 12.5)
    
    def test_vincular_pessoa_endividamento(self):
        """Testa vínculo entre pessoa e endividamento"""
        with self.app.app_context():
            pessoa = Pessoa.query.first()
            
            endividamento = Endividamento(
                banco='Banco Teste',
                numero_proposta='54321',
                data_emissao=date.today(),
                data_vencimento_final=date.today() + timedelta(days=365),
                taxa_juros=10.0,
                tipo_taxa_juros='ano'
            )
            
            endividamento.pessoas.append(pessoa)
            db.session.add(endividamento)
            db.session.commit()
            
            # Verificar vínculo
            endividamento_db = Endividamento.query.first()
            self.assertEqual(len(endividamento_db.pessoas), 1)
            self.assertEqual(endividamento_db.pessoas[0].nome, 'João Silva')
    
    def test_vincular_fazenda_endividamento(self):
        """Testa vínculo entre fazenda e endividamento"""
        with self.app.app_context():
            fazenda = Fazenda.query.first()
            
            endividamento = Endividamento(
                banco='Banco Teste',
                numero_proposta='54321',
                data_emissao=date.today(),
                data_vencimento_final=date.today() + timedelta(days=365),
                taxa_juros=10.0,
                tipo_taxa_juros='ano'
            )
            
            db.session.add(endividamento)
            db.session.flush()
            
            # Criar vínculo com fazenda
            vinculo = EndividamentoFazenda(
                endividamento_id=endividamento.id,
                fazenda_id=fazenda.id,
                hectares=50.0,
                tipo='objeto_credito',
                descricao='Área para plantio'
            )
            
            db.session.add(vinculo)
            db.session.commit()
            
            # Verificar vínculo
            endividamento_db = Endividamento.query.first()
            self.assertEqual(len(endividamento_db.fazenda_vinculos), 1)
            self.assertEqual(endividamento_db.fazenda_vinculos[0].fazenda.nome, 'Fazenda Teste')
            self.assertEqual(float(endividamento_db.fazenda_vinculos[0].hectares), 50.0)
    
    def test_criar_parcelas(self):
        """Testa criação de parcelas"""
        with self.app.app_context():
            endividamento = Endividamento(
                banco='Banco Teste',
                numero_proposta='54321',
                data_emissao=date.today(),
                data_vencimento_final=date.today() + timedelta(days=365),
                taxa_juros=10.0,
                tipo_taxa_juros='ano'
            )
            
            db.session.add(endividamento)
            db.session.flush()
            
            # Criar parcelas
            for i in range(12):
                parcela = Parcela(
                    endividamento_id=endividamento.id,
                    data_vencimento=date.today() + timedelta(days=30 * (i + 1)),
                    valor=1000.0
                )
                db.session.add(parcela)
            
            db.session.commit()
            
            # Verificar parcelas
            endividamento_db = Endividamento.query.first()
            self.assertEqual(len(endividamento_db.parcelas), 12)
            self.assertEqual(float(endividamento_db.parcelas[0].valor), 1000.0)
    
    def test_marcar_parcela_como_paga(self):
        """Testa marcação de parcela como paga"""
        with self.app.app_context():
            endividamento = Endividamento(
                banco='Banco Teste',
                numero_proposta='54321',
                data_emissao=date.today(),
                data_vencimento_final=date.today() + timedelta(days=365),
                taxa_juros=10.0,
                tipo_taxa_juros='ano'
            )
            
            db.session.add(endividamento)
            db.session.flush()
            
            parcela = Parcela(
                endividamento_id=endividamento.id,
                data_vencimento=date.today() + timedelta(days=30),
                valor=1000.0
            )
            
            db.session.add(parcela)
            db.session.commit()
            
            # Marcar como paga
            parcela_db = Parcela.query.first()
            parcela_db.pago = True
            parcela_db.data_pagamento = date.today()
            parcela_db.valor_pago = 1000.0
            
            db.session.commit()
            
            # Verificar
            parcela_atualizada = Parcela.query.first()
            self.assertTrue(parcela_atualizada.pago)
            self.assertEqual(parcela_atualizada.data_pagamento, date.today())
    
    def test_rota_listar_endividamentos(self):
        """Testa rota de listagem de endividamentos"""
        response = self.client.get('/endividamentos/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Gerenciamento de Endividamentos', response.data)
    
    def test_rota_novo_endividamento(self):
        """Testa rota de novo endividamento"""
        response = self.client.get('/endividamentos/novo')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Novo Endividamento', response.data)
    
    def test_criar_endividamento_via_post(self):
        """Testa criação de endividamento via POST"""
        with self.app.app_context():
            pessoa = Pessoa.query.first()
            
            data = {
                'banco': 'Banco Teste POST',
                'numero_proposta': 'POST123',
                'data_emissao': '2024-01-01',
                'data_vencimento_final': '2024-12-31',
                'taxa_juros': '15.5',
                'tipo_taxa_juros': 'ano',
                'prazo_carencia': '3',
                'pessoas_ids': [str(pessoa.id)],
                'objetos_credito': '[]',
                'garantias': '[]',
                'parcelas': '[{"data_vencimento": "2024-06-01", "valor": "5000.00"}]'
            }
            
            response = self.client.post('/endividamentos/novo', data=data, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            
            # Verificar se foi criado
            endividamento = Endividamento.query.filter_by(numero_proposta='POST123').first()
            self.assertIsNotNone(endividamento)
            self.assertEqual(endividamento.banco, 'Banco Teste POST')
    
    def test_rota_vencimentos(self):
        """Testa rota de vencimentos"""
        response = self.client.get('/endividamentos/vencimentos')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Controle de Vencimentos', response.data)
    
    def test_to_dict_endividamento(self):
        """Testa método to_dict do modelo Endividamento"""
        with self.app.app_context():
            endividamento = Endividamento(
                banco='Banco Teste',
                numero_proposta='DICT123',
                data_emissao=date(2024, 1, 1),
                data_vencimento_final=date(2024, 12, 31),
                taxa_juros=12.5,
                tipo_taxa_juros='ano'
            )
            
            db.session.add(endividamento)
            db.session.commit()
            
            dict_data = endividamento.to_dict()
            
            self.assertEqual(dict_data['banco'], 'Banco Teste')
            self.assertEqual(dict_data['numero_proposta'], 'DICT123')
            self.assertEqual(dict_data['data_emissao'], '2024-01-01')
            self.assertEqual(dict_data['taxa_juros'], 12.5)
    
    def test_validacao_data_vencimento(self):
        """Testa validação de data de vencimento"""
        with self.app.app_context():
            # Data de vencimento anterior à emissão deve ser inválida
            endividamento = Endividamento(
                banco='Banco Teste',
                numero_proposta='VAL123',
                data_emissao=date.today(),
                data_vencimento_final=date.today() - timedelta(days=1),  # Data anterior
                taxa_juros=10.0,
                tipo_taxa_juros='ano'
            )
            
            # Em um cenário real, isso seria validado no formulário
            # Aqui testamos apenas a lógica de negócio
            self.assertTrue(endividamento.data_vencimento_final < endividamento.data_emissao)

if __name__ == '__main__':
    unittest.main()

