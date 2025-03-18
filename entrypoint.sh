#!/bin/bash
# entrypoint.sh

# Rodar os testes com pytest e cobertura
echo "Running tests..."
pytest tests/ --cov=app --cov=services --cov-report=term-missing

# Verificar o resultado dos testes
if [ $? -eq 0 ]; then
    echo "Tests passed, starting application..."
    # Iniciar a aplicação com Gunicorn
    exec gunicorn --bind 0.0.0.0:${SERVICE_PORT:-5000} --workers ${GUNICORN_WORKERS:-2} --timeout ${GUNICORN_TIMEOUT:-120} app:app
else
    echo "Tests failed, exiting..."
    exit 1
fi