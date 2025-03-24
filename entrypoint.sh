#!/bin/bash
# entrypoint.sh

# Mostrar informações iniciais
echo "Starting application..."

# Execute run_swagger.sh
./run_swagger.sh

# Verificar se está em modo de teste
if [ "${TESTING}" != "True" ]; then
    echo "Running tests before starting the application..."
    
    # Executar testes
    ./run_tests.sh
    
    # Verificar resultado dos testes
    TEST_RESULT=$?
    if [ $TEST_RESULT -ne 0 ]; then
        echo "Tests failed with exit code $TEST_RESULT. Aborting application startup."
        exit $TEST_RESULT
    fi
    
    echo "Tests passed successfully! Starting Gunicorn..."
    
    # Iniciar o Gunicorn
    exec gunicorn \
        --bind 0.0.0.0:${SERVICE_PORT:-5000} \
        --workers ${GUNICORN_WORKERS:-2} \
        --timeout ${GUNICORN_TIMEOUT:-120} \
        --access-logfile - \
        --error-logfile - \
        app:app
else
    echo "Running in test mode. Skipping application startup."
fi