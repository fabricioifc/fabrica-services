#!/bin/bash

# Instala dependências de teste
pip install -r requirements-test.txt

# Executa os testes com cobertura
pytest --cov=. --cov-report=term-missing --cov-report=html:coverage_report

# Exibe o relatório de cobertura
echo "Relatório de cobertura gerado em ./coverage_report/index.html"