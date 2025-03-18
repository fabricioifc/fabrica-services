from flask import Flask, request, jsonify
from services.email_service import enviar_email, validar_configuracoes
import logging
import time
import os

# Configurações da aplicação a partir de variáveis de ambiente
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "5000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
DEBUG_MODE = os.getenv("FLASK_DEBUG", "False").lower() == "true"

# Mapear string de nível de log para constantes do logging
log_levels = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}

# Configurar aplicação Flask
app = Flask(__name__)

# Garantir que o diretório de logs existe
os.makedirs("logs", exist_ok=True)

# Configurar logging
logging.basicConfig(
    level=log_levels.get(LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join("logs", "api.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("email-api")

# Endpoint para verificação de saúde do serviço
@app.route('/health', methods=['GET'])
def health_check():
    try:
        config = validar_configuracoes()  # Deve ser mockado
        return jsonify({
            "status": "ok",
            "timestamp": time.time(),
            "service": "email-service",
            "version": "1.0",
            "smtp_server": config["smtp_server"],
            "email_configured": bool(config["remetente"]),
            "port": SERVICE_PORT,
            "environment": "production" if not DEBUG_MODE else "development",
            "log_level": LOG_LEVEL
        })
    except Exception as e:
        logger.error(f"Falha na verificação de saúde: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": time.time(),
            "service": "email-service"
        }), 500

# Endpoint para envio de email
@app.route('/api/enviar-email', methods=['POST'])
def api_enviar_email():
    try:
        logger.info(f"Requisição recebida de {request.remote_addr}")
        
        # Tentar obter os dados JSON, tratando exceções específicas
        try:
            dados = request.json
        except Exception as e:
            logger.warning(f"Erro ao parsear JSON: {str(e)}")
            return jsonify({
                "sucesso": False,
                "mensagem": "Nenhum dado fornecido ou formato JSON inválido"
            }), 400
        
        if not dados:
            logger.warning("Requisição sem dados")
            return jsonify({
                "sucesso": False,
                "mensagem": "Nenhum dado fornecido"
            }), 400
        
        campos_obrigatorios = ['destinatario', 'assunto', 'corpo']
        for campo in campos_obrigatorios:
            if campo not in dados:
                logger.warning(f"Campo obrigatório ausente: {campo}")
                return jsonify({
                    "sucesso": False,
                    "mensagem": f"Campo obrigatório ausente: {campo}"
                }), 400
        
        debug_mode = dados.get('debug', False)
        resultado = enviar_email(
            destinatario=dados['destinatario'],
            assunto=dados['assunto'],
            corpo=dados['corpo'],
            debug=debug_mode
        )
        
        if resultado["sucesso"]:
            logger.info(f"Email enviado com sucesso para {dados['destinatario']}")
        else:
            logger.error(f"Falha ao enviar email: {resultado['mensagem']}")
        
        status_code = 200 if resultado["sucesso"] else 500
        return jsonify(resultado), status_code
        
    except Exception as e:
        logger.exception("Erro não tratado na API")
        return jsonify({
            "sucesso": False,
            "mensagem": "Erro no servidor ao processar a solicitação",
            "detalhes": str(e)
        }), 500

# Rota raiz para documentação básica
@app.route('/', methods=['GET'])
def documentacao():
    return jsonify({
        "service": "Email Service API",
        "version": "1.0",
        "endpoints": {
            "/health": "GET - Verificação de saúde do serviço",
            "/api/enviar-email": "POST - Envio de email"
        },
        "documentation": "Para mais informações, consulte a documentação interna",
        "port": SERVICE_PORT,
        "mode": "development" if DEBUG_MODE else "production"
    })

if __name__ == '__main__':
    # Usar apenas para desenvolvimento local
    app.run(debug=DEBUG_MODE, host='0.0.0.0', port=SERVICE_PORT)