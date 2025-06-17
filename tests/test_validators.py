import pytest
from src.utils.validators import validate_email, validate_cpf, validate_cnpj, sanitize_input

def test_validate_email():
    # Válidos
    assert validate_email('test@example.com')
    assert validate_email('user.name@domain.co.uk')
    assert validate_email('user+tag@example.org')
    # Inválidos
    assert not validate_email('invalid-email')
    assert not validate_email('@example.com')
    assert not validate_email('test@')
    assert not validate_email('')

def test_validate_cpf():
    # Válidos
    assert validate_cpf('11144477735')
    assert validate_cpf('111.444.777-35')
    # Inválidos
    assert not validate_cpf('11111111111')  # Todos iguais
    assert not validate_cpf('123456789')    # Muito curto
    assert not validate_cpf('12345678901')  # Dígitos verificadores incorretos
    assert not validate_cpf('')

def test_validate_cnpj():
    # Válidos
    assert validate_cnpj('11222333000181')
    assert validate_cnpj('11.222.333/0001-81')
    # Inválidos
    assert not validate_cnpj('11111111111111')  # Todos iguais
    assert not validate_cnpj('123456789')       # Muito curto
    assert not validate_cnpj('12345678901234')  # Dígitos verificadores incorretos
    assert not validate_cnpj('')

def test_sanitize_input():
    # Remove tags HTML
    assert sanitize_input('<script>alert("xss")</script>') == 'alert("xss")'
    assert sanitize_input('<b>texto</b>') == 'texto'
    # Remove caracteres de controle
    assert sanitize_input('texto\x00\x1f') == 'texto'
    # Remove espaços desnecessários
    assert sanitize_input('  texto normal  ') == 'texto normal'
    # Entrada vazia
    assert sanitize_input('') == ''
    assert sanitize_input(None) is None