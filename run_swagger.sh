#!/bin/bash
# Salve este script como fix-swagger.sh na raiz do seu projeto
# Execute dentro do container

# 1. Encontrar a localização do pacote flask-swagger-ui
SWAGGER_PATH=$(python -c "import flask_swagger_ui; print(flask_swagger_ui.__path__[0])")
echo "Pacote flask-swagger-ui encontrado em: $SWAGGER_PATH"

# 2. Criar diretório para os arquivos estáticos
mkdir -p /app/static/swagger-ui
echo "Diretório de destino criado: /app/static/swagger-ui"

# 3. Copiar todos os arquivos do Swagger UI
echo "Copiando arquivos do Swagger UI..."
cp -R $SWAGGER_PATH/dist/* /app/static/swagger-ui/

# 4. Verificar se os arquivos essenciais foram copiados
for file in "swagger-ui-bundle.js" "swagger-ui-standalone-preset.js" "swagger-ui.css"; do
    if [ -f "/app/static/swagger-ui/$file" ]; then
        echo "✓ $file copiado com sucesso"
    else
        echo "✗ ERRO: $file não encontrado!"
    fi
done

# 5. Criar um arquivo index.html personalizado para o Swagger UI
cat > /app/static/swagger-ui/index.html << 'EOL'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>API de Envio de Email - Documentação</title>
    <!-- Caminhos corrigidos com prefixo /services -->
    <link rel="stylesheet" type="text/css" href="/services/static/swagger-ui/swagger-ui.css">
    <link rel="icon" type="image/png" href="/services/static/swagger-ui/favicon-32x32.png" sizes="32x32">
    <style>
        html { box-sizing: border-box; overflow: -moz-scrollbars-vertical; overflow-y: scroll; }
        *, *:before, *:after { box-sizing: inherit; }
        body { margin: 0; background: #fafafa; }
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    
    <!-- Caminhos corrigidos com prefixo /services -->
    <script src="/services/static/swagger-ui/swagger-ui-bundle.js"></script>
    <script src="/services/static/swagger-ui/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {
            // Configuração do Swagger UI com caminho corrigido para swagger.json
            const ui = SwaggerUIBundle({
                url: "/services/static/swagger.json",
                dom_id: "#swagger-ui",
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout"
            });
            window.ui = ui;
        };
    </script>
</body>
</html>
EOL

echo "Arquivo index.html personalizado criado"

# 6. Ajustar permissões
chmod -R 755 /app/static/swagger-ui/

echo "Configuração do Swagger UI concluída!"