#!/usr/bin/env bash
# Déploiement d'EcoShop sur le VPS : récupère la dernière version de main,
# reconstruit et relance les conteneurs.
# Lancé par le workflow de CD, ou à la main depuis le dossier du projet.
set -euo pipefail

cd "$(dirname "$0")/.."

COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"

echo "Mise à jour du code"
git fetch --quiet origin main
git checkout --quiet main
git pull --quiet --ff-only origin main

echo "Construction et démarrage des conteneurs"
$COMPOSE --profile airflow up -d --build --remove-orphans

echo "Activation du DAG quotidien"
for attempt in $(seq 1 30); do
    if docker exec ecoshop-airflow airflow dags unpause ecoshop_quotidien \
        >/dev/null 2>&1; then
        break
    fi
    sleep 10
done

echo "Déploiement terminé : $(git rev-parse --short HEAD)"
