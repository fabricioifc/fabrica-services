#!/bin/bash
# run_tests.sh

echo "Running tests..."

# Executar testes com pytest e coverage
python -m pytest --cov=app tests/ -v

# Capturar o resultado dos testes
TEST_RESULT=$?

# Gerar relatório de cobertura
python -m coverage html -d coverage_report

# Resumo da cobertura
echo ""
echo "Test coverage summary:"
python -m coverage report

# Retornar o resultado dos testes
if [ $TEST_RESULT -eq 0 ]; then
    echo "All tests passed successfully!"
else
    echo "Tests failed with exit code $TEST_RESULT"
fi

# Importante: retornar o código de saída dos testes
exit $TEST_RESULT