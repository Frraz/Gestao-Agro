# Utilitários para validação e segurança
from flask import request, abort
from werkzeug.security import generate_password_hash, check_password_hash
import re
from functools import wraps

def validate_email(email):
    """Valida formato de e-mail"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_cpf(cpf):
    """Valida CPF brasileiro"""
    # Remove caracteres não numéricos
    cpf = re.sub(r'[^0-9]', '', cpf)
    
    # Verifica se tem 11 dígitos
    if len(cpf) != 11:
        return False
    
    # Verifica se todos os dígitos são iguais
    if cpf == cpf[0] * 11:
        return False
    
    # Validação do primeiro dígito verificador
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto
    
    if int(cpf[9]) != digito1:
        return False
    
    # Validação do segundo dígito verificador
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto
    
    return int(cpf[10]) == digito2

def validate_cnpj(cnpj):
    """Valida CNPJ brasileiro"""
    # Remove caracteres não numéricos
    cnpj = re.sub(r'[^0-9]', '', cnpj)
    
    # Verifica se tem 14 dígitos
    if len(cnpj) != 14:
        return False
    
    # Verifica se todos os dígitos são iguais
    if cnpj == cnpj[0] * 14:
        return False
    
    # Validação do primeiro dígito verificador
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * pesos1[i] for i in range(12))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto
    
    if int(cnpj[12]) != digito1:
        return False
    
    # Validação do segundo dígito verificador
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * pesos2[i] for i in range(13))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto
    
    return int(cnpj[13]) == digito2

def sanitize_input(text):
    """Sanitiza entrada de texto removendo caracteres perigosos"""
    if not text:
        return text
    
    # Remove tags HTML básicas
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove caracteres de controle
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    return text.strip()

def validate_file_extension(filename, allowed_extensions):
    """Valida extensão de arquivo"""
    if not filename:
        return False
    
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def hash_password(password):
    """Gera hash seguro da senha"""
    return generate_password_hash(password)

def verify_password(password, password_hash):
    """Verifica senha contra hash"""
    return check_password_hash(password_hash, password)

def require_auth(f):
    """Decorator para rotas que requerem autenticação"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Implementar lógica de autenticação aqui
        # Por enquanto, apenas um placeholder
        return f(*args, **kwargs)
    return decorated_function

def validate_required_fields(data, required_fields):
    """Valida se todos os campos obrigatórios estão presentes"""
    missing_fields = []
    for field in required_fields:
        if field not in data or not data[field]:
            missing_fields.append(field)
    
    return missing_fields

def validate_numeric_field(value, min_value=None, max_value=None):
    """Valida campo numérico"""
    try:
        num_value = float(value)
        if min_value is not None and num_value < min_value:
            return False
        if max_value is not None and num_value > max_value:
            return False
        return True
    except (ValueError, TypeError):
        return False

