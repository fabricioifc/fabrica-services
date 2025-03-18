import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/email_logs.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("email_sender")

# Carregar variáveis de ambiente
load_dotenv()

def validar_configuracoes() -> Dict[str, Any]:
    """Valida se todas as configurações necessárias estão presentes."""
    config = {
        "smtp_server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
        "porta": int(os.getenv("SMTP_PORT", "587")),
        "remetente": os.getenv("EMAIL_HOST_USER", ""),
        "senha": os.getenv("EMAIL_HOST_PASSWORD", ""),
        "use_tls": os.getenv("EMAIL_USE_TLS", "True").lower() == "true"
    }
    
    # Verificar valores obrigatórios
    if not config["remetente"]:
        raise ValueError("EMAIL_HOST_USER não está configurado no arquivo .env")
    if not config["senha"]:
        raise ValueError("EMAIL_HOST_PASSWORD não está configurado no arquivo .env")
    
    return config

def enviar_email(destinatario: str, assunto: str, corpo: str, debug: bool = False) -> Dict[str, Any]:
    """
    Envia um email e retorna um dicionário com o status e informações adicionais.
    
    Args:
        destinatario: Email do destinatário
        assunto: Assunto do email
        corpo: Corpo do email em HTML
        debug: Modo debug para exibir informações sensíveis em logs
        
    Returns:
        Dict contendo o status do envio e informações adicionais
    """
    resultado = {
        "sucesso": False,
        "mensagem": "",
        "detalhes": None
    }
    
    # Validar parâmetros de entrada
    if not destinatario or "@" not in destinatario:
        resultado["mensagem"] = "Endereço de email do destinatário inválido"
        logger.error(f"Email inválido: {destinatario}")
        return resultado
    
    if not assunto:
        resultado["mensagem"] = "Assunto não pode estar vazio"
        logger.error("Tentativa de envio com assunto vazio")
        return resultado
    
    if not corpo:
        resultado["mensagem"] = "Corpo do email não pode estar vazio"
        logger.error("Tentativa de envio com corpo vazio")
        return resultado
    
    try:
        # Obter e validar configurações
        config = validar_configuracoes()
        
        # Criando mensagem
        mensagem = MIMEMultipart()
        mensagem["From"] = config["remetente"]
        mensagem["To"] = destinatario
        mensagem["Subject"] = assunto
        
        # Anexando corpo da mensagem
        mensagem.attach(MIMEText(corpo, "html"))
        
        # Log de informações (omitindo detalhes sensíveis no modo não-debug)
        logger.info(f"Preparando envio para: {destinatario}")
        logger.info(f"Assunto: {assunto}")
        if debug:
            logger.debug(f"Usando servidor: {config['smtp_server']}:{config['porta']}")
            logger.debug(f"Remetente: {config['remetente']}")
            logger.debug(f"Corpo: {corpo[:100]}...")
        
        # Conectando ao servidor com timeout
        servidor = smtplib.SMTP(config["smtp_server"], config["porta"], timeout=10)
        
        # Verificar status da conexão
        status_code, _ = servidor.ehlo()
        if status_code != 250:
            raise smtplib.SMTPConnectError(status_code, "Falha na conexão com o servidor SMTP")
        
        # Ativar TLS se configurado
        if config["use_tls"]:
            servidor.starttls()
            status_code, _ = servidor.ehlo()
            if status_code != 250:
                raise smtplib.SMTPException("Falha ao iniciar TLS")
        
        # Login
        servidor.login(config["remetente"], config["senha"])
        
        # Enviar email
        texto = mensagem.as_string()
        status = servidor.sendmail(config["remetente"], destinatario, texto)
        
        # Verificar resultado do envio
        if status:
            # O método sendmail retorna um dicionário vazio se todos os destinatários foram aceitos
            resultado["mensagem"] = f"Problemas com alguns destinatários: {status}"
            resultado["detalhes"] = status
            logger.warning(f"Email enviado com avisos: {status}")
        else:
            resultado["sucesso"] = True
            resultado["mensagem"] = "Email enviado com sucesso!"
            logger.info("Email enviado com sucesso!")
        
        # Fechar conexão
        servidor.quit()
        
    except ValueError as e:
        # Erro de configuração
        resultado["mensagem"] = f"Erro de configuração: {str(e)}"
        resultado["detalhes"] = str(e)
        logger.error(f"Erro de configuração: {str(e)}")
        
    except smtplib.SMTPAuthenticationError as e:
        # Erro de autenticação
        resultado["mensagem"] = "Falha na autenticação. Verifique usuário e senha."
        resultado["detalhes"] = str(e)
        logger.error(f"Erro de autenticação SMTP: {str(e)}")
        
    except smtplib.SMTPConnectError as e:
        # Erro de conexão
        resultado["mensagem"] = "Não foi possível conectar ao servidor SMTP."
        resultado["detalhes"] = str(e)
        logger.error(f"Erro de conexão SMTP: {str(e)}")
        
    except smtplib.SMTPServerDisconnected as e:
        # Servidor desconectou
        resultado["mensagem"] = "Servidor SMTP desconectou inesperadamente."
        resultado["detalhes"] = str(e)
        logger.error(f"Servidor SMTP desconectou: {str(e)}")
        
    except smtplib.SMTPException as e:
        # Outros erros SMTP
        resultado["mensagem"] = f"Erro SMTP: {str(e)}"
        resultado["detalhes"] = str(e)
        logger.error(f"Erro SMTP: {str(e)}")
        
    except Exception as e:
        # Erros genéricos
        resultado["mensagem"] = f"Erro inesperado: {str(e)}"
        resultado["detalhes"] = str(e)
        logger.error(f"Erro inesperado ao enviar email: {str(e)}", exc_info=True)
        
    return resultado