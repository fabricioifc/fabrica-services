import json
from flask import Flask

def test_health_check_success(client, mock_validar_configuracoes):
    mock_validar_configuracoes.return_value = {
        "smtp_server": "smtp.test.com",
        "porta": 587,
        "remetente": "test@test.com",
        "senha": "password",
        "use_tls": True
    }
    
    response = client.get('/health')
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data["status"] == "ok"
    assert data["smtp_server"] == "smtp.test.com"
    assert data["email_configured"] is True

def test_health_check_failure(client, mock_validar_configuracoes):
    mock_validar_configuracoes.side_effect = ValueError("Configuração inválida")
    
    response = client.get('/health')
    data = json.loads(response.data)
    
    assert response.status_code == 500
    assert data["status"] == "error"
    assert "Configuração inválida" in data["message"]

def test_enviar_email_success(client, mock_enviar_email):
    mock_enviar_email.return_value = {
        "sucesso": True,
        "mensagem": "Email enviado com sucesso!",
        "detalhes": None
    }
    
    payload = {
        "destinatario": "test@example.com",
        "assunto": "Test Subject",
        "corpo": "<h1>Test Body</h1>",
        "debug": False
    }
    
    response = client.post('/api/enviar-email', json=payload)
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data["sucesso"] is True
    assert data["mensagem"] == "Email enviado com sucesso!"

def test_enviar_email_missing_field(client):
    payload = {
        "destinatario": "test@example.com",
        "corpo": "<h1>Test Body</h1>"
    }
    
    response = client.post('/api/enviar-email', json=payload)
    data = json.loads(response.data)
    
    assert response.status_code == 400
    assert data["sucesso"] is False
    assert "Campo obrigatório ausente: assunto" in data["mensagem"]

def test_enviar_email_no_data(client):
    response = client.post('/api/enviar-email', 
                         content_type='application/json', 
                         data=None)
    data = json.loads(response.data)
    
    assert response.status_code == 400
    assert data["sucesso"] is False
    assert "Nenhum dado fornecido" in data["mensagem"]

def test_enviar_email_server_error(client, mock_enviar_email):
    mock_enviar_email.side_effect = Exception("Erro interno")
    
    payload = {
        "destinatario": "test@example.com",
        "assunto": "Test Subject",
        "corpo": "<h1>Test Body</h1>"
    }
    
    response = client.post('/api/enviar-email', json=payload)
    data = json.loads(response.data)
    
    assert response.status_code == 500
    assert data["sucesso"] is False
    assert "Erro no servidor" in data["mensagem"]