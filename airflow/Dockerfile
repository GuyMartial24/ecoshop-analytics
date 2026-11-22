# Image Airflow d'EcoShop : même version que l'Airflow de production (3.3.2, Python 3.12).
#
# Deux environnements Python séparés, pour éviter tout conflit de dépendances :
# - celui d'Airflow, auquel on ajoute uniquement Cosmos (orchestration dbt) ;
# - /opt/ecoshop-venv, construit depuis uv.lock, qui contient dbt, dlt et Elementary
#   dans les versions exactes utilisées en développement.
FROM apache/airflow:3.3.2-python3.12

# uv, copié depuis son image officielle (version figée)
COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /usr/local/bin/uv

# 1. Cosmos dans l'environnement d'Airflow. Airflow est réépinglé pour qu'aucune
#    dépendance ne puisse le mettre à jour par effet de bord.
RUN pip install --no-cache-dir "apache-airflow==3.3.2" "astronomer-cosmos==1.16.0"

# 2. Environnement isolé du projet (dbt, dlt, Elementary...), identique à uv.lock
USER root
COPY pyproject.toml uv.lock /tmp/ecoshop/
RUN cd /tmp/ecoshop \
    && UV_PROJECT_ENVIRONMENT=/opt/ecoshop-venv UV_PYTHON_DOWNLOADS=never \
       uv sync --frozen --no-install-project --no-cache \
    && chown -R airflow: /opt/ecoshop-venv \
    && rm -rf /tmp/ecoshop
USER airflow
