"""
Tests for the enhanced buscar-pessoas endpoint with cache and pagination
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from src.main import create_app
from src.models.db import db
from src.models.pessoa import Pessoa


@pytest.fixture
def app():
    """Create application for testing"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['REDIS_URL'] = 'redis://localhost:6379/1'  # Use test database
    
    with app.app_context():
        db.create_all()
        
        # Create test data
        pessoa1 = Pessoa(nome="João Silva", cpf_cnpj="12345678901", email="joao@test.com")
        pessoa2 = Pessoa(nome="Maria Silva", cpf_cnpj="98765432100", email="maria@test.com")
        pessoa3 = Pessoa(nome="Pedro Santos", cpf_cnpj="11111111111", email="pedro@test.com")
        
        db.session.add_all([pessoa1, pessoa2, pessoa3])
        db.session.commit()
        
        yield app
        
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


def test_buscar_pessoas_backward_compatibility(client):
    """Test that the endpoint maintains backward compatibility"""
    response = client.get('/endividamentos/buscar-pessoas?q=Silva')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    
    # Should return array format (not paginated)
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]['nome'] == 'João Silva'
    assert data[1]['nome'] == 'Maria Silva'


def test_buscar_pessoas_with_pagination(client):
    """Test pagination functionality"""
    response = client.get('/endividamentos/buscar-pessoas?q=Silva&page=1&limit=1')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    
    # Should return paginated format
    assert isinstance(data, dict)
    assert 'data' in data
    assert 'pagination' in data
    
    # Check data
    assert len(data['data']) == 1
    assert data['data'][0]['nome'] == 'João Silva'
    
    # Check pagination metadata
    pagination = data['pagination']
    assert pagination['page'] == 1
    assert pagination['limit'] == 1
    assert pagination['total'] == 2
    assert pagination['has_next'] is True
    assert pagination['has_prev'] is False
    assert pagination['total_pages'] == 2


def test_buscar_pessoas_second_page(client):
    """Test second page of results"""
    response = client.get('/endividamentos/buscar-pessoas?q=Silva&page=2&limit=1')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    
    assert len(data['data']) == 1
    assert data['data'][0]['nome'] == 'Maria Silva'
    
    pagination = data['pagination']
    assert pagination['page'] == 2
    assert pagination['has_next'] is False
    assert pagination['has_prev'] is True


def test_buscar_pessoas_minimum_chars(client):
    """Test minimum character requirement"""
    response = client.get('/endividamentos/buscar-pessoas?q=J')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data == []


def test_buscar_pessoas_limit_validation(client):
    """Test limit parameter validation"""
    # Test maximum limit
    response = client.get('/endividamentos/buscar-pessoas?q=Silva&limit=100')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    
    # Should be capped at 50
    assert data['pagination']['limit'] == 50


def test_buscar_pessoas_page_validation(client):
    """Test page parameter validation"""
    # Test negative page
    response = client.get('/endividamentos/buscar-pessoas?q=Silva&page=-1')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    
    # Should default to page 1
    assert data['pagination']['page'] == 1


@patch('src.routes.endividamento.cache')
def test_buscar_pessoas_cache_usage(mock_cache, client):
    """Test that cache is used correctly"""
    # Setup mock
    mock_cache.get.return_value = None  # Cache miss
    mock_cache.set.return_value = True
    
    response = client.get('/endividamentos/buscar-pessoas?q=Silva')
    
    assert response.status_code == 200
    
    # Verify cache was checked and set
    mock_cache.get.assert_called_once()
    mock_cache.set.assert_called_once()
    
    # Verify cache key format
    cache_key = mock_cache.get.call_args[0][0]
    assert cache_key.startswith('buscar_pessoas:Silva:')


@patch('src.routes.endividamento.cache')
def test_buscar_pessoas_cache_hit(mock_cache, client):
    """Test cache hit scenario"""
    # Setup mock to return cached data
    cached_data = [{'id': 1, 'nome': 'Cached Result'}]
    mock_cache.get.return_value = cached_data
    
    response = client.get('/endividamentos/buscar-pessoas?q=Silva')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    
    # Should return cached data
    assert data == cached_data
    
    # Should not call set (data was from cache)
    mock_cache.set.assert_not_called()


def test_pessoa_crud_cache_invalidation():
    """Test that CRUD operations invalidate cache"""
    from src.utils.performance import clear_related_cache
    from src.utils.cache import cache
    
    with patch.object(cache, 'clear_pattern') as mock_clear:
        clear_related_cache("pessoa")
        
        # Verify that buscar_pessoas cache pattern is cleared
        mock_clear.assert_any_call("buscar_pessoas:*")
        mock_clear.assert_any_call("pessoas:*")
        mock_clear.assert_any_call("dashboard:*")