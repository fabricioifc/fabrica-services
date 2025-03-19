#!/bin/bash
# entrypoint.sh

# Mostrar informações iniciais
echo "Starting application..."

# Iniciar o Gunicorn
exec gunicorn \
    --bind 0.0.0.0:${SERVICE_PORT:-5000} \
    --workers ${GUNICORN_WORKERS:-2} \
    --timeout ${GUNICORN_TIMEOUT:-120} \
    app:app