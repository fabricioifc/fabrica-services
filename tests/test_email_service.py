import pytest
import smtplib  # Adicionado o import necessário
from services.email_service import enviar_email, validar_configuracoes

def test_validar_configuracoes_success(mocker):
    mocker.patch('os.getenv', side_effect=[
        "smtp.test.com", "587", "test@test.com", "password", "True"
    ])
    
    config = validar_configuracoes()
    
    assert config["smtp_server"] == "smtp.test.com"
    assert config["porta"] == 587
    assert config["remetente"] == "test@test.com"
    assert config["use_tls"] is True

def test_validar_configuracoes_missing_credentials(mocker):
    mocker.patch('os.getenv', side_effect=["smtp.test.com", "587", "", "", "True"])
    
    with pytest.raises(ValueError) as exc:
        validar_configuracoes()
    assert "EMAIL_HOST_USER" in str(exc.value)

def test_enviar_email_invalid_recipient():
    result = enviar_email("", "Test", "Body")
    
    assert result["sucesso"] is False
    assert "inválido" in result["mensagem"]

def test_enviar_email_empty_subject():
    result = enviar_email("test@example.com", "", "Body")
    
    assert result["sucesso"] is False
    assert "Assunto não pode estar vazio" in result["mensagem"]

def test_enviar_email_empty_body():
    result = enviar_email("test@example.com", "Test", "")
    
    assert result["sucesso"] is False
    assert "Corpo do email não pode estar vazio" in result["mensagem"]

def test_enviar_email_success(mocker):
    mocker.patch('services.email_service.validar_configuracoes', return_value={
        "smtp_server": "smtp.test.com",
        "porta": 587,
        "remetente": "test@test.com",
        "senha": "password",
        "use_tls": True
    })
    mock_smtp = mocker.patch('smtplib.SMTP')
    mock_instance = mock_smtp.return_value
    mock_instance.ehlo.return_value = (250, b"OK")
    mock_instance.sendmail.return_value = {}
    
    result = enviar_email("test@example.com", "Test", "<h1>Body</h1>")
    
    assert mock_instance.login.called
    assert mock_instance.sendmail.called
    assert result["sucesso"] is True
    assert result["mensagem"] == "Email enviado com sucesso!"

def test_enviar_email_smtp_auth_error(mocker):
    mocker.patch('services.email_service.validar_configuracoes', return_value={
        "smtp_server": "smtp.test.com",
        "porta": 587,
        "remetente": "test@test.com",
        "senha": "password",
        "use_tls": True
    })
    mock_smtp = mocker.patch('smtplib.SMTP')
    mock_instance = mock_smtp.return_value
    mock_instance.ehlo.return_value = (250, b"OK")
    mock_instance.login.side_effect = smtplib.SMTPAuthenticationError(535, "Auth failed")
    
    result = enviar_email("test@example.com", "Test", "<h1>Body</h1>")
    
    assert result["sucesso"] is False
    assert "Falha na autenticação" in result["mensagem"]