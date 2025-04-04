#!/bin/bash

# Parâmetros
GITHUB_URL=https://github.com/fabricioifc/fabrica-services.git
NETWORK_NAME=fabrica-service
NETWORK_NAME_NGINX=fabrica-nginx-proxy-network
DOCKER_COMPOSE_FILE=docker-compose.yml
DOCKER_COMPOSE_BUILD=true
BRANCH=main
ENVIRONMENT=${1}  # dev|development|prod|production

# Função para exibir mensagens de erro e sair
error_exit() {
    echo "Erro: $1"
    exit 1
}

# Função para ambiente de desenvolvimento
deploy_development() {
    echo "Executando deploy em ambiente de DESENVOLVIMENTO..."
    
    # Parar os containers em execução
    echo "Parando os containers..."
    docker compose down || error_exit "Não foi possível parar os containers"
    
    # Subir os containers novamente com build
    echo "Subindo os containers com build..."
    docker compose -f $DOCKER_COMPOSE_FILE up -d --build || error_exit "Não foi possível subir os containers"
    
    echo "Deploy de desenvolvimento finalizado com sucesso!"
}

# Função para ambiente de produção
deploy_production() {
    echo "Executando deploy em ambiente de PRODUÇÃO..."
    
    # Verificar se o branch existe no repositório remoto do GitHub antes de fazer o deploy
    echo "Verificando se o branch '$BRANCH' existe no repositório remoto do GitHub..."
    if [ ! "$(git ls-remote --heads $GITHUB_URL $BRANCH)" ]; then
        error_exit "O branch $BRANCH não existe no repositório remoto do GitHub"
    fi
    
    # Parar os containers em execução
    echo "Parando os containers..."
    docker compose down || error_exit "Não foi possível parar os containers"
    
    # Puxar as últimas mudanças do GitHub
    echo "Puxando as últimas mudanças do GitHub..."
    git pull origin $BRANCH || error_exit "Não foi possível puxar as últimas mudanças do GitHub ($BRANCH)"
    
    # Criar a rede NETWORK_NAME se ela não existir
    if [ ! "$(docker network ls --format '{{.Name}}' | grep $NETWORK_NAME)" ]; then
        echo "Criando a rede $NETWORK_NAME..."
        docker network create $NETWORK_NAME || error_exit "Não foi possível criar a rede $NETWORK_NAME"
    fi
    
    # Subir os containers novamente com as novas mudanças
    echo "Subindo os containers..."
    if [ "$DOCKER_COMPOSE_BUILD" = true ]; then
        docker compose -f $DOCKER_COMPOSE_FILE up -d --build || error_exit "Não foi possível subir os containers"
    else
        docker compose -f $DOCKER_COMPOSE_FILE up -d || error_exit "Não foi possível subir os containers"
    fi
    
    # Verificar se a rede NETWORK_NAME_NGINX está conectada ao container fabrica-prod-web
    if [ ! "$(docker network inspect -f '{{range .Containers}}{{.Name}}{{end}}' $NETWORK_NAME_NGINX | grep $NETWORK_NAME)" ]; then
        echo "Conectando a rede $NETWORK_NAME_NGINX ao container $NETWORK_NAME"
        docker network connect $NETWORK_NAME_NGINX ${NETWORK_NAME} || error_exit "Não foi possível conectar a rede $NETWORK_NAME_NGINX ao container $NETWORK_NAME"
    fi
    
    echo "Deploy de produção finalizado com sucesso!"
}

# Executar o deploy de acordo com o ambiente especificado
case "$ENVIRONMENT" in
    development|dev)
        deploy_development
        ;;
    production|prod)
        deploy_production
        ;;
    *)
        error_exit "Ambiente inválido. Use 'development' ou 'production'."
        ;;
esac