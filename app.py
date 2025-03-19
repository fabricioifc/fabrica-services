from flask import Flask, request, jsonify, Blueprint
from services.email_service import enviar_email, validar_configuracoes
import logging
import time
import os

# Configurações da aplicação a partir de variáveis de ambiente
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "5000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
DEBUG_MODE = os.getenv("FLASK_DEBUG", "False").lower() == "true"
APPLICATION_ROOT = os.getenv("APPLICATION_ROOT", "")  # Prefixo da aplicação, vazio por padrão

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

# Criar Blueprint para a API principal
api_bp = Blueprint('api', __name__)

# Endpoint para verificação de saúde do serviço
@api_bp.route('/health', methods=['GET'])
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
@api_bp.route('/api/enviar-email', methods=['POST'])
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
@api_bp.route('/', methods=['GET'])
def index():  # Mudamos o nome da função para 'index'
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

# Registrar o blueprint com o prefixo se configurado
if APPLICATION_ROOT:
    app.register_blueprint(api_bp, url_prefix=APPLICATION_ROOT)
else:
    app.register_blueprint(api_bp)

# Corrigindo o problema: criamos uma função que implementa diretamente a mesma lógica
# em vez de tentar acessar a função pelo nome no dicionário view_functions
services_bp = Blueprint('services', __name__, url_prefix='/services')

@services_bp.route('/health', methods=['GET'])
def services_health_check():
    return health_check()  # Chamamos a função diretamente

@services_bp.route('/api/enviar-email', methods=['POST'])
def services_api_enviar_email():
    return api_enviar_email()  # Chamamos a função diretamente

@services_bp.route('/', methods=['GET'])
def services_index():
    # Implementamos a mesma lógica diretamente
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

app.register_blueprint(services_bp)

# Adicionar rotas de fallback para diferentes combinações de prefixos
@app.route('/services', methods=['GET'])
def services_root():
    return services_index()  # Chamamos a função diretamente

if __name__ == '__main__':
    # Usar apenas para desenvolvimento local
    app.run(debug=DEBUG_MODE, host='0.0.0.0', port=SERVICE_PORT)