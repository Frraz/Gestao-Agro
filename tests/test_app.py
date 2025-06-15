# Testes unitários para o sistema de gestão agro
import unittest
import os
import sys
import tempfile
import json

# Adicionar o diretório pai ao PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.main import create_app
from src.models.db import db
from src.utils.validators import validate_email, validate_cpf, validate_cnpj, sanitize_input

class TestValidators(unittest.TestCase):
    """Testes para funções de validação"""
    
    def test_validate_email(self):
        """Testa validação de e-mail"""
        # E-mails válidos
        self.assertTrue(validate_email('test@example.com'))
        self.assertTrue(validate_email('user.name@domain.co.uk'))
        self.assertTrue(validate_email('user+tag@example.org'))
        
        # E-mails inválidos
        self.assertFalse(validate_email('invalid-email'))
        self.assertFalse(validate_email('@example.com'))
        self.assertFalse(validate_email('test@'))
        self.assertFalse(validate_email(''))
    
    def test_validate_cpf(self):
        """Testa validação de CPF"""
        # CPFs válidos
        self.assertTrue(validate_cpf('11144477735'))
        self.assertTrue(validate_cpf('111.444.777-35'))
        
        # CPFs inválidos
        self.assertFalse(validate_cpf('11111111111'))  # Todos iguais
        self.assertFalse(validate_cpf('123456789'))    # Muito curto
        self.assertFalse(validate_cpf('12345678901'))  # Dígitos verificadores incorretos
        self.assertFalse(validate_cpf(''))
    
    def test_validate_cnpj(self):
        """Testa validação de CNPJ"""
        # CNPJs válidos
        self.assertTrue(validate_cnpj('11222333000181'))
        self.assertTrue(validate_cnpj('11.222.333/0001-81'))
        
        # CNPJs inválidos
        self.assertFalse(validate_cnpj('11111111111111'))  # Todos iguais
        self.assertFalse(validate_cnpj('123456789'))       # Muito curto
        self.assertFalse(validate_cnpj('12345678901234'))  # Dígitos verificadores incorretos
        self.assertFalse(validate_cnpj(''))
    
    def test_sanitize_input(self):
        """Testa sanitização de entrada"""
        # Teste com tags HTML
        self.assertEqual(sanitize_input('<script>alert("xss")</script>'), 'alert("xss")')
        self.assertEqual(sanitize_input('<b>texto</b>'), 'texto')
        
        # Teste com caracteres de controle
        self.assertEqual(sanitize_input('texto\x00\x1f'), 'texto')
        
        # Teste com entrada normal
        self.assertEqual(sanitize_input('  texto normal  '), 'texto normal')
        
        # Teste com entrada vazia
        self.assertEqual(sanitize_input(''), '')
        self.assertEqual(sanitize_input(None), None)

class TestApp(unittest.TestCase):
    """Testes para a aplicação Flask"""
    
    def setUp(self):
        """Configuração antes de cada teste"""
        self.db_fd, self.db_path = tempfile.mkstemp()
        test_config = {
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': f'sqlite:///{self.db_path}',
            'SECRET_KEY': 'test_secret_key'
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
    
    def tearDown(self):
        """Limpeza após cada teste"""
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_index_redirect(self):
        """Testa redirecionamento da página inicial"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)  # Redirecionamento
    
    def test_health_check(self):
        """Testa endpoint de health check"""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['database'], 'connected')
    
    def test_404_error(self):
        """Testa página não encontrada"""
        response = self.client.get('/pagina-inexistente')
        self.assertEqual(response.status_code, 404)

if __name__ == '__main__':
    unittest.main()

