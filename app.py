from flask import Flask, request, jsonify, Blueprint
from flask_cors import CORS  # Importa a biblioteca CORS
from services.email_service import enviar_email, validar_configuracoes
import logging
import time
import os

# Configurações da aplicação a partir de variáveis de ambiente
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "5000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
DEBUG_MODE = os.getenv("FLASK_DEBUG", "False").lower() == "true"
APPLICATION_ROOT = os.getenv("APPLICATION_ROOT", "")  # Prefixo da aplicação, vazio por padrão

# Configuração do Flask
app = Flask(__name__)

# Ativando CORS para todas as rotas e origens
# CORS(app, resources={r"/api/*": {"origins": "*"}})
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:8000", "https://fsw-ifc.brdrive.net"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Configurar logging
logging.basicConfig(
    level=logging.getLevelName(LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("email-api")

# Criar Blueprint para a API principal
api_bp = Blueprint('api', __name__)
CORS(api_bp)  # Aplica CORS ao Blueprint também

@api_bp.route('/health', methods=['GET'])
def health_check():
    try:
        config = validar_configuracoes()
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
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route('/api/enviar-email', methods=['POST', 'OPTIONS'])
def api_enviar_email():
    if request.method == 'OPTIONS':
        return '', 204  # Resposta para pré-requisição CORS

    # Verifica se há dados no corpo da requisição
    if not request.data or request.data == b'':
        return jsonify({
            "sucesso": False,
            "mensagem": "Nenhum dado fornecido"
        }), 400
    try:
        logger.info(f"Requisição recebida de {request.remote_addr}")
        dados = request.get_json()

        if not dados:
            return jsonify({"sucesso": False, "mensagem": "Nenhum dado fornecido"}), 400

        campos_obrigatorios = ['destinatario', 'assunto', 'corpo']
        for campo in campos_obrigatorios:
            if campo not in dados:
                return jsonify({"sucesso": False, "mensagem": f"Campo obrigatório ausente: {campo}"}), 400

        resultado = enviar_email(
            destinatario=dados['destinatario'],
            assunto=dados['assunto'],
            corpo=dados['corpo'],
            debug=dados.get('debug', False)
        )

        return jsonify(resultado), 200 if resultado["sucesso"] else 500

    except Exception as e:
        logger.exception("Erro não tratado na API")
        return jsonify({"sucesso": False, "mensagem": "Erro no servidor"}), 500

app.register_blueprint(api_bp)

if __name__ == '__main__':
    app.run(debug=DEBUG_MODE, host='0.0.0.0', port=SERVICE_PORT)
