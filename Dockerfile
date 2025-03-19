ARG PYTHON_VERSION=3.13
FROM python:${PYTHON_VERSION}-slim

# Definir variáveis de ambiente para uso durante a build
ARG SERVICE_PORT=5000
ENV SERVICE_PORT=${SERVICE_PORT}

WORKDIR /app

# Instalar dependências do sistema incluindo curl para healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar arquivos de requisitos primeiro (para aproveitar o cache do Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o código da aplicação e testes
COPY . .

# Executar os testes durante o build
RUN pytest tests/ --cov=app --cov=services --cov-report=term-missing --cov-fail-under=75

# Criar diretório para logs e definir permissões
RUN mkdir -p /app/logs && chmod 755 /app/logs

# Copiar e tornar o script de entrypoint executável
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Expor a porta configurável
EXPOSE ${SERVICE_PORT}

# Definir o entrypoint para iniciar a aplicação
ENTRYPOINT ["./entrypoint.sh"]