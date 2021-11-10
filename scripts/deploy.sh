#!/bin/bash

set -e

export DEPLOY_ENV=$1
export DEPLOY_HOST=$2

COMPOSE_OPTS="--compress"
if [[ "$3" == "--no-cache" ]] || [[ "$4" == "--no-cache" ]]; then
    # Add --no-cache to build to disable cache and rebuild documentation.
    COMPOSE_OPTS="$COMPOSE_OPTS --no-cache"
fi

if [[ $DEPLOY_HOST ]]; then
    export DOCKER_HOST="ssh://$DEPLOY_HOST"
    echo "DOCKER_HOST set to $DOCKER_HOST"
fi
export COMPOSE_PROJECT_NAME=lutrisweb_$DEPLOY_ENV
if [[ $DEPLOY_ENV == "prod" ]]; then
    export POSTGRES_HOST_PORT=5435
    export HTTP_PORT=82
    source ./.env.prod
else
    export POSTGRES_HOST_PORT=5433
    export HTTP_PORT=81
    source ./.env
fi

echo ------------ 1 ------------
docker-compose --verbose -f docker-compose.prod.yml build $COMPOSE_OPTS lutrisweb

echo ------------ 2 ------------
docker-compose --verbose -f docker-compose.prod.yml build $COMPOSE_OPTS lutrisworker

echo ------------ 3 ------------
docker-compose -f docker-compose.prod.yml build $COMPOSE_OPTS lutrisnginx

echo "Bringing Docker Compose up"
echo ------------ 4 ------------
# 第一次可能会失败，所以执行两次
docker-compose -f docker-compose.prod.yml up -d || docker-compose -f docker-compose.prod.yml up -d

if [[ "$3" == "--merge" ]] || [[ "$4" == "--merge" ]]; then
    echo ------------ a ------------
    docker-compose -f docker-compose.prod.yml exec lutrisweb ./manage.py makemigrations --merge

    echo ------------ b ------------
    docker-compose -f docker-compose.prod.yml exec lutrisweb ./manage.py migrate
fi

echo "Restarting NGinx"
echo ------------ 5 ------------
docker-compose -f docker-compose.prod.yml restart lutrisnginx
