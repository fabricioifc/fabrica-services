from flask import Flask, request, jsonify, Blueprint, abort, render_template
from flask_cors import CORS
from services.email_service import enviar_email, validar_configuracoes
import logging
import time
import os
import re
import secrets
from functools import wraps
import bleach
from email_validator import validate_email, EmailNotValidError
import json
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.exceptions import BadRequest
from flask_swagger_ui import get_swaggerui_blueprint

# Configurações de aplicação
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "5000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
DEBUG_MODE = os.getenv("FLASK_DEBUG", "False").lower() == "true"
APPLICATION_ROOT = os.getenv("APPLICATION_ROOT", "")
API_KEY = os.getenv("API_KEY", "")  # Chave de API para autenticação

if not API_KEY:
    raise ValueError("API_KEY não configurada")

# Listas de origens permitidas
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# Configuração do Flask
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False  # Previne que o JSON seja reordenado
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024  # Limite de tamanho do payload (1MB)
app.config['API_KEY'] = API_KEY  # Adicionar API_KEY ao config

# Configuração do limitador de taxa
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["100 per day", "20 per hour"],
    storage_uri="memory://",
)

# Configuração do CORS com restrições de origem
CORS(app, resources={
    r"/*": {  # Alterado para cobrir todos os endpoints
        "origins": ALLOWED_ORIGINS,
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-API-KEY"],
        "expose_headers": ["Content-Length", "X-Request-ID"],
        "supports_credentials": False,  # Não permite cookies de autenticação
        "max_age": 600  # Cache CORS por 10 minutos
    }
})

# Configurar logging com rotação
if not os.path.exists("logs"):
    os.makedirs("logs")

logging.basicConfig(
    level=logging.getLevelName(LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s',
    handlers=[
        logging.FileHandler("logs/api.log"),
        logging.StreamHandler()
    ]
)

# Filtro personalizado para adicionar request_id aos logs
class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = getattr(request, 'id', 'no-request-id')
        return True

logger = logging.getLogger("email-api")
logger.addFilter(RequestIdFilter())

# Configuração do Swagger
SWAGGER_URL = '/api/docs'  # URL para acessar a UI do Swagger
API_URL = '/static/swagger.json'  # Onde o arquivo de especificação Swagger está localizado

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "API de Envio de Email"
    }
)

# Middleware para adicionar request_id a todas as solicitações
@app.before_request
def before_request():
    request.id = secrets.token_hex(8)  # ID único para cada solicitação
    
    # Log de todas as requisições recebidas
    logger.debug(f"Requisição recebida: {request.method} {request.path} de {request.remote_addr}")
    
    # Verificar apenas para os endpoints não-OPTIONS
    if request.method != 'OPTIONS':
        # Verificar o tamanho do conteúdo
        content_length = request.headers.get('Content-Length')
        if content_length and int(content_length) > app.config['MAX_CONTENT_LENGTH']:
            abort(413)  # Payload too large

# Função para proteger rotas com autenticação por API key
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        provided_key = request.headers.get('X-API-KEY')
        api_key = app.config.get('API_KEY', API_KEY)  # Prefer config value
        if not provided_key or not secrets.compare_digest(provided_key, api_key):
            logger.warning(f"Tentativa de acesso não autorizado de {request.remote_addr}")
            return jsonify({"sucesso": False, "mensagem": "Não autorizado"}), 401
        return f(*args, **kwargs)
    return decorated_function

# Função para sanitizar entrada
def sanitize_input(data):
    if isinstance(data, dict):
        return {k: sanitize_input(v) for k, v in data.items()}
    elif isinstance(data, str):
        return bleach.clean(data, tags=[], attributes={}, strip=True)
    else:
        return data

# Função para validar email
def validate_email_address(email):
    try:
        validate_email(email)
        return True
    except EmailNotValidError:
        return False

# Criar Blueprint para a API principal
api_bp = Blueprint('api', __name__)

@api_bp.route('/health', methods=['GET'])
@limiter.limit("10 per minute")
def health_check():
    try:
        config = validar_configuracoes()
        return jsonify({
            "status": "ok",
            "timestamp": time.time(),
            "service": "email-service",
            "version": "1.0",
            "environment": "production" if not DEBUG_MODE else "development"
        })
    except Exception as e:
        logger.error(f"Falha na verificação de saúde: {str(e)}")
        return jsonify({"status": "error", "message": "Serviço indisponível"}), 500

@api_bp.route('/enviar-email', methods=['POST', 'OPTIONS'])
@limiter.limit("50 per minute")  # Limite de taxa específico para envio de email
@require_api_key  # Proteção com API key
def api_enviar_email():
    if request.method == 'OPTIONS':
        return '', 204  # Resposta para pré-requisição CORS
    
    # Verificar Content-Type
    if not request.is_json:
        return jsonify({
            "sucesso": False,
            "mensagem": "Formato de requisição inválido, esperado application/json"
        }), 415
    
    # Verificar se há dados no corpo da requisição
    if not request.data or request.data == b'':
        return jsonify({
            "sucesso": False,
            "mensagem": "Nenhum dado fornecido"
        }), 400
    
    try:
        logger.info(f"Requisição recebida de {request.remote_addr}")
        
        # Limitar tamanho do payload
        if len(request.data) > 100 * 1024:  # 100KB para o corpo da mensagem
            return jsonify({
                "sucesso": False,
                "mensagem": "Payload excede o limite permitido"
            }), 413
        
        # Validar e sanitizar a entrada
        try:
            dados = request.get_json()
            if not dados:
                return jsonify({"sucesso": False, "mensagem": "Nenhum dado fornecido"}), 400
            
            # Sanitizar todos os dados de entrada
            dados = sanitize_input(dados)
        except json.JSONDecodeError:
            return jsonify({"sucesso": False, "mensagem": "JSON inválido"}), 400
        
        # Validar campos obrigatórios
        campos_obrigatorios = ['destinatario', 'assunto', 'corpo']
        for campo in campos_obrigatorios:
            if campo not in dados:
                return jsonify({"sucesso": False, "mensagem": f"Campo obrigatório ausente: {campo}"}), 400
        
        # Validar email do destinatário
        if not validate_email_address(dados['destinatario']):
            return jsonify({"sucesso": False, "mensagem": "Email do destinatário inválido"}), 400
        
        
        # Verificar tamanho dos campos
        if len(dados['assunto']) > 200:
            return jsonify({"sucesso": False, "mensagem": "Assunto muito longo"}), 400
        
        if len(dados['corpo']) > 50000:
            return jsonify({"sucesso": False, "mensagem": "Corpo do email muito longo"}), 400
        
        # Processar envio do email
        resultado = enviar_email(
            destinatario=dados['destinatario'],
            assunto=dados['assunto'],
            corpo=dados['corpo'],
            debug=False  # Nunca permitir debug em produção
        )
        
        # Criar log do resultado sem expor detalhes sensíveis
        if resultado["sucesso"]:
            logger.info(f"Email enviado com sucesso para {dados['destinatario']}")
        else:
            logger.error(f"Falha ao enviar email: {resultado.get('mensagem', 'Erro desconhecido')}")
        
        return jsonify(resultado), 200 if resultado["sucesso"] else 500
    except BadRequest:
        return jsonify({"sucesso": False, "mensagem": "JSON malformado"}), 400
    except Exception as e:
        logger.exception("Erro não tratado na API")
        return jsonify({"sucesso": False, "mensagem": "Erro no servidor"}), 500

# Rota para documentação de endpoints
@api_bp.route('/endpoints', methods=['GET'])
def api_endpoints():
    """
    Retorna uma listagem e documentação dos endpoints disponíveis.
    """
    endpoints = [
        {
            "endpoint": "/api/health",
            "método": "GET",
            "descrição": "Verificação de status da API",
            "requer_autenticação": False,
            "parâmetros": [],
            "resposta_exemplo": {
                "status": "ok",
                "timestamp": time.time(),
                "service": "email-service",
                "version": "1.0",
                "environment": "production"
            }
        },
        {
            "endpoint": "/api/enviar-email",
            "método": "POST",
            "descrição": "Envia um email para o destinatário especificado",
            "requer_autenticação": True,
            "headers": [
                {"nome": "X-API-KEY", "descrição": "Chave de API para autenticação"},
                {"nome": "Content-Type", "descrição": "Deve ser application/json"}
            ],
            "parâmetros": [
                {"nome": "destinatario", "tipo": "string", "descrição": "Email do destinatário"},
                {"nome": "assunto", "tipo": "string", "descrição": "Assunto do email (máximo 200 caracteres)"},
                {"nome": "corpo", "tipo": "string", "descrição": "Corpo do email em HTML (máximo 50000 caracteres)"}
            ],
            "resposta_exemplo": {
                "sucesso": True,
                "mensagem": "Email enviado com sucesso!"
            },
            "limites": "50 requisições por minuto"
        },
        {
            "endpoint": "/api/endpoints",
            "método": "GET",
            "descrição": "Retorna documentação dos endpoints disponíveis",
            "requer_autenticação": False,
            "parâmetros": [],
            "resposta_exemplo": "Este documento"
        },
        {
            "endpoint": "/api/docs",
            "método": "GET",
            "descrição": "Interface Swagger para documentação da API",
            "requer_autenticação": False,
            "parâmetros": []
        }
    ]
    
    # Adicionar informação sobre a base da URL
    base_url_info = {
        "nota": "Estes endpoints podem ser acessados via o prefixo '/services' no domínio principal, por exemplo: https://fsw-ifc.brdrive.net/services/api/health"
    }
    
    return jsonify({
        "serviço": "API de Envio de Email",
        "versão": "1.0",
        "endpoints": endpoints,
        "informações_adicionais": base_url_info
    })

# Rota raiz para redirecionamento para a documentação
@app.route('/', methods=['GET'])
def root():
    return jsonify({
        "mensagem": "API de Envio de Email",
        "versão": "1.0",
        "documentação": "/api/docs",
        "endpoints": "/api/endpoints",
        "status": "/api/health"
    })

# Registrar os blueprints
app.register_blueprint(api_bp, url_prefix='/api')  # Mantém o url_prefix /api
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

# Manipuladores de erro personalizados
@app.errorhandler(404)
def not_found(e):
    return jsonify({"sucesso": False, "mensagem": "Endpoint não encontrado"}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"sucesso": False, "mensagem": "Método não permitido"}), 405

@app.errorhandler(413)
def payload_too_large(e):
    return jsonify({"sucesso": False, "mensagem": "Payload muito grande"}), 413

@app.errorhandler(429)
def rate_limit_exceeded(e):
    return jsonify({"sucesso": False, "mensagem": "Taxa limite excedida. Tente novamente mais tarde."}), 429

@app.errorhandler(500)
def server_error(e):
    logger.exception("Erro interno do servidor")
    return jsonify({"sucesso": False, "mensagem": "Erro interno do servidor"}), 500

@app.errorhandler(415)
def unsupported_media_type(error):
    return jsonify({"sucesso": False, "mensagem": "Content-Type não suportado"}), 415

@app.errorhandler(400)
def bad_request(error):
    return jsonify({"sucesso": False, "mensagem": "Requisição inválida"}), 400

# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=SERVICE_PORT, debug=DEBUG_MODE)