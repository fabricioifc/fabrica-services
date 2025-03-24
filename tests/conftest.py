import pytest
from unittest.mock import patch, MagicMock
import os
import json
from app import app

@pytest.fixture
def client():
    """Fixture que configura o cliente de teste Flask."""
    app.config['TESTING'] = True
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
        "API_KEY": "test-api-key"
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
    with patch('app.validate_email') as mock:
        # Por padrão, emails válidos retornam True
        def side_effect(email):
            if '@' in email and '.' in email:
                return True
            raise ValueError("Email inválido")
        
        mock.side_effect = side_effect
        yield mock