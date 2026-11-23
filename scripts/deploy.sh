#!/usr/bin/env bash
# Déploiement d'EcoShop sur le VPS : récupère main, reconstruit les
# conteneurs, applique les modèles dbt puis redéploie la couche sémantique
# et les dashboards Lightdash.
# Lancé par le workflow de CD (clé SSH restreinte à ce script), ou à la main.
#
# Tout le script est dans une fonction : bash le lit entièrement avant de
# l'exécuter, ce qui évite les problèmes quand git pull le met à jour.
set -euo pipefail

main() {
    cd "$(dirname "$0")/.."

    local compose="docker compose -f docker-compose.yml -f docker-compose.prod.yml"

    echo "Mise à jour du code"
    git fetch --quiet origin main
    git checkout --quiet main
    git pull --quiet --ff-only origin main

    set -a
    # shellcheck disable=SC1091
    source .env
    set +a

    echo "Construction et démarrage des conteneurs"
    $compose --profile airflow up -d --build --remove-orphans

    echo "Attente d'Airflow"
    for _ in $(seq 1 30); do
        if curl -fsS -m 5 "http://127.0.0.1:${AIRFLOW_PORT}/api/v2/monitor/health" \
            >/dev/null 2>&1; then
            break
        fi
        sleep 10
    done

    echo "Modèles dbt"
    in_airflow sh -c "cd dbt_project && dbt deps && dbt build --target prod"

    echo "Couche sémantique et dashboards Lightdash"
    in_airflow lightdash deploy --project "$LIGHTDASH_PROJECT_UUID" \
        --project-dir dbt_project --profiles-dir dbt_project \
        --target prod --select marts --assume-yes
    in_airflow lightdash upload --path lightdash --force \
        --project "$LIGHTDASH_PROJECT_UUID"
    in_airflow lightdash validate --project "$LIGHTDASH_PROJECT_UUID" \
        --project-dir dbt_project --profiles-dir dbt_project \
        --target prod --select marts

    echo "Activation du DAG quotidien"
    docker exec ecoshop-airflow airflow dags unpause ecoshop_quotidien \
        >/dev/null

    echo "Déploiement terminé : $(git rev-parse --short HEAD)"
}

# Commande lancée dans le conteneur Airflow (dbt, dlt et CLI Lightdash)
in_airflow() {
    docker exec -w /opt/ecoshop -e HOME=/tmp -e CI=true \
        -e LIGHTDASH_API_KEY="$LIGHTDASH_API_KEY" \
        -e LIGHTDASH_URL=http://lightdash:8080 \
        -e PATH=/opt/ecoshop-venv/bin:/usr/local/bin:/usr/bin:/bin \
        ecoshop-airflow "$@"
}

main "$@"
exit
