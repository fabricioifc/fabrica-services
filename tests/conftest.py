# tests/conftest.py
import pytest
from app import app

@pytest.fixture
def client(mocker):
    # Mockar os.getenv com valores padrão válidos
    mocker.patch('os.getenv', side_effect=lambda key, default=None: {
        "SERVICE_PORT": "5000",
        "SMTP_PORT": "587",
        "SMTP_SERVER": "smtp.test.com",
        "EMAIL_HOST_USER": "test@test.com",
        "EMAIL_HOST_PASSWORD": "password",
        "EMAIL_USE_TLS": "True",
        "FLASK_DEBUG": "False",
        "LOG_LEVEL": "INFO"
    }.get(key, default))
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def mock_enviar_email(mocker):
    # Garantir que o patch seja aplicado corretamente
    return mocker.patch('app.enviar_email', autospec=True)  # Mudar para o escopo correto

@pytest.fixture
def mock_validar_configuracoes(mocker):
    # Garantir que o patch seja aplicado corretamente
    return mocker.patch('app.validar_configuracoes', autospec=True)  # Mudar para o escopo correto