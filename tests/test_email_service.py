import pytest
from unittest.mock import patch, MagicMock
import smtplib
from services.email_service import enviar_email, validar_configuracoes

def test_validar_configuracoes(mock_env_variables):
    """Testa a função validar_configuracoes com variáveis de ambiente válidas."""
    config = validar_configuracoes()
    
    assert config["smtp_server"] == "smtp.test.com"
    assert config["porta"] == 587
    assert config["remetente"] == "test@test.com"
    assert config["senha"] == "test-password"
    assert config["use_tls"] is True

def test_validar_configuracoes_sem_remetente(monkeypatch):
    """Testa validar_configuracoes quando o remetente não está configurado."""
    monkeypatch.delenv("EMAIL_HOST_USER", raising=False)
    
    with pytest.raises(ValueError) as excinfo:
        validar_configuracoes()
    
    assert "EMAIL_HOST_USER" in str(excinfo.value)

def test_validar_configuracoes_sem_senha(monkeypatch):
    """Testa validar_configuracoes quando a senha não está configurada."""
    monkeypatch.setenv("EMAIL_HOST_USER", "test@test.com")
    monkeypatch.delenv("EMAIL_HOST_PASSWORD", raising=False)
    
    with pytest.raises(ValueError) as excinfo:
        validar_configuracoes()
    
    assert "EMAIL_HOST_PASSWORD" in str(excinfo.value)

def test_enviar_email_sucesso(mock_smtp, mock_env_variables):
    """Testa enviar_email com sucesso."""
    resultado = enviar_email(
        destinatario="test@example.com",
        assunto="Teste",
        corpo="<p>Corpo do email</p>"
    )
    
    assert resultado["sucesso"] is True
    assert "sucesso" in resultado["mensagem"].lower()
    
    # Verificar se o mock SMTP foi chamado corretamente
    mock_smtp.assert_called_once_with("smtp.test.com", 587, timeout=10)
    smtp_instance = mock_smtp.return_value
    assert smtp_instance.starttls.called
    assert smtp_instance.login.called
    assert smtp_instance.sendmail.called
    assert smtp_instance.quit.called

def test_enviar_email_destinatario_invalido():
    """Testa enviar_email com destinatário inválido."""
    resultado = enviar_email(
        destinatario="invalido",
        assunto="Teste",
        corpo="<p>Corpo do email</p>"
    )
    
    assert resultado["sucesso"] is False
    assert "inválido" in resultado["mensagem"].lower()

def test_enviar_email_assunto_vazio():
    """Testa enviar_email com assunto vazio."""
    resultado = enviar_email(
        destinatario="test@example.com",
        assunto="",
        corpo="<p>Corpo do email</p>"
    )
    
    assert resultado["sucesso"] is False
    assert "assunto" in resultado["mensagem"].lower()

def test_enviar_email_corpo_vazio():
    """Testa enviar_email com corpo vazio."""
    resultado = enviar_email(
        destinatario="test@example.com",
        assunto="Teste",
        corpo=""
    )
    
    assert resultado["sucesso"] is False
    assert "corpo" in resultado["mensagem"].lower()

def test_enviar_email_erro_autenticacao(mock_smtp, mock_env_variables):
    """Testa enviar_email com erro de autenticação."""
    # Configurar mock para simular erro de autenticação
    smtp_instance = mock_smtp.return_value
    smtp_instance.login.side_effect = smtplib.SMTPAuthenticationError(535, "Authentication failed")
    
    resultado = enviar_email(
        destinatario="test@example.com",
        assunto="Teste",
        corpo="<p>Corpo do email</p>"
    )
    
    assert resultado["sucesso"] is False
    assert "autenticação" in resultado["mensagem"].lower()

def test_enviar_email_erro_conexao(mock_smtp, mock_env_variables):
    """Testa enviar_email com erro de conexão."""
    # Configurar mock para simular erro de conexão
    smtp_instance = mock_smtp.return_value
    smtp_instance.ehlo.return_value = (421, b"Service not available")
    
    resultado = enviar_email(
        destinatario="test@example.com",
        assunto="Teste",
        corpo="<p>Corpo do email</p>"
    )
    
    assert resultado["sucesso"] is False
    assert "conectar" in resultado["mensagem"].lower() or "conexão" in resultado["mensagem"].lower()

def test_enviar_email_servidor_desconectado(mock_smtp, mock_env_variables):
    """Testa enviar_email com servidor desconectado."""
    # Configurar mock para simular servidor desconectado
    smtp_instance = mock_smtp.return_value
    smtp_instance.sendmail.side_effect = smtplib.SMTPServerDisconnected("Server disconnected")
    
    resultado = enviar_email(
        destinatario="test@example.com",
        assunto="Teste",
        corpo="<p>Corpo do email</p>"
    )
    
    assert resultado["sucesso"] is False
    assert "desconect" in resultado["mensagem"].lower()

def test_enviar_email_erro_smtp_generico(mock_smtp, mock_env_variables):
    """Testa enviar_email com erro SMTP genérico."""
    # Configurar mock para simular erro SMTP genérico
    smtp_instance = mock_smtp.return_value
    smtp_instance.sendmail.side_effect = smtplib.SMTPException("SMTP error")
    
    resultado = enviar_email(
        destinatario="test@example.com",
        assunto="Teste",
        corpo="<p>Corpo do email</p>"
    )
    
    assert resultado["sucesso"] is False
    assert "smtp" in resultado["mensagem"].lower()

def test_enviar_email_erro_inesperado(mock_smtp, mock_env_variables):
    """Testa enviar_email com erro inesperado."""
    # Configurar mock para simular erro inesperado
    smtp_instance = mock_smtp.return_value
    smtp_instance.sendmail.side_effect = Exception("Unexpected error")
    
    resultado = enviar_email(
        destinatario="test@example.com",
        assunto="Teste",
        corpo="<p>Corpo do email</p>"
    )
    
    assert resultado["sucesso"] is False
    assert "inesperado" in resultado["mensagem"].lower()

def test_enviar_email_problemas_destinatarios(mock_smtp, mock_env_variables):
    """Testa enviar_email com problemas em alguns destinatários."""
    # Configurar mock para simular problemas em alguns destinatários
    smtp_instance = mock_smtp.return_value
    smtp_instance.sendmail.return_value = {"falha@example.com": (550, "Mailbox not found")}
    
    resultado = enviar_email(
        destinatario="test@example.com",
        assunto="Teste",
        corpo="<p>Corpo do email</p>"
    )
    
    assert resultado["sucesso"] is False
    assert "problemas" in resultado["mensagem"].lower()
    assert resultado["detalhes"] is not None

def test_enviar_email_falha_tls(mock_smtp, mock_env_variables):
    """Testa enviar_email com falha ao iniciar TLS."""
    # Configurar mock para simular falha ao iniciar TLS
    smtp_instance = mock_smtp.return_value
    smtp_instance.starttls.side_effect = smtplib.SMTPException("TLS startup failed")
    
    resultado = enviar_email(
        destinatario="test@example.com",
        assunto="Teste",
        corpo="<p>Corpo do email</p>"
    )
    
    assert resultado["sucesso"] is False
    assert "tls" in resultado["mensagem"].lower() or "erro smtp" in resultado["mensagem"].lower()