import pytest
from unittest.mock import patch, MagicMock
import os
import json
from app import app
import importlib

@pytest.fixture(scope='session', autouse=True)
def disable_limiter():
    """
    Fixture que desativa completamente o limitador no início da sessão de teste.
    Esta é uma abordagem mais direta que modifica o objeto limiter diretamente.
    """
    # Importar o módulo app com o objeto limiter
    try:
        # Obter referência ao limitador diretamente do módulo app
        from app import limiter
        
        # Substituir o método limit por uma versão que não faz nada
        original_limit = limiter.limit
        
        def dummy_limit(*args, **kwargs):
            def decorator(f):
                return f
            return decorator
        
        # Substituir o método no objeto limiter
        limiter.limit = dummy_limit
        
        # Desativar completamente o limitador
        if hasattr(limiter, 'enabled'):
            limiter.enabled = False
        
        # Desativar em configurações específicas
        app.config['RATELIMIT_ENABLED'] = False
        
        yield
        
        # Restaurar o método original (opcionalmente)
        limiter.limit = original_limit
        
    except (ImportError, AttributeError) as e:
        # Se não conseguirmos encontrar o limitador, apenas continuamos
        print(f"Aviso: Não foi possível desativar o limitador: {e}")
        yield

@pytest.fixture
def client():
    """Fixture que configura o cliente de teste Flask."""
    app.config['TESTING'] = True
    app.config['RATELIMIT_ENABLED'] = False
    
    with app.test_client() as client:
        # Configurar cabeçalho de API key por padrão
        client.environ_base['HTTP_X_API_KEY'] = os.getenv("API_KEY", "test-api-key")
        yield client

@pytest.fixture
def mock_env_variables(monkeypatch):
    """Fixture que configura variáveis de ambiente para teste."""
    env_vars = {
        "SMTP_SERVER": "smtp.test.com",
        "SMTP_PORT": "587",
        "EMAIL_HOST_USER": "test@test.com",
        "EMAIL_HOST_PASSWORD": "test-password",
        "EMAIL_USE_TLS": "True",
        "API_KEY": "test-api-key",
        "TESTING": "True"
    }
    
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    
    yield env_vars

@pytest.fixture
def mock_smtp():
    """Fixture que cria um mock para o servidor SMTP."""
    with patch('smtplib.SMTP') as mock:
        # Configurar o comportamento padrão do mock
        smtp_instance = MagicMock()
        # Configurar ehlo para retornar código 250 (sucesso)
        smtp_instance.ehlo.return_value = (250, b'OK')
        # Configurar sendmail para retornar um dicionário vazio (sucesso)
        smtp_instance.sendmail.return_value = {}
        
        mock.return_value = smtp_instance
        yield mock

@pytest.fixture
def valid_email_payload():
    """Fixture que retorna uma carga útil válida para envio de email."""
    return {
        "destinatario": "destinatario@example.com",
        "assunto": "Teste de Email",
        "corpo": "<p>Este é um email de teste.</p>"
    }

@pytest.fixture
def invalid_email_payload():
    """Fixture que retorna uma carga útil inválida para envio de email."""
    return {
        "destinatario": "invalid-email",
        "assunto": "Teste de Email",
        "corpo": "<p>Este é um email de teste.</p>"
    }

@pytest.fixture
def email_validator_mock():
    """Fixture que configura um mock para o validador de email."""
    with patch('app.validate_email_address') as mock:
        # Por padrão, emails válidos retornam True
        def side_effect(email):
            if '@' in email and '.' in email:
                return True
            return False  # Retorne False em vez de lançar uma exceção
        
        mock.side_effect = side_effect
        yield mock