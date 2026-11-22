# Airflow 3.3.2 (même version qu'en production) + Cosmos.
# dbt, dlt et Elementary sont dans un venv séparé (/opt/ecoshop-venv).
FROM apache/airflow:3.3.2-python3.12

COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /usr/local/bin/uv

# Airflow réépinglé pour ne pas être mis à jour par Cosmos
RUN pip install --no-cache-dir "apache-airflow==3.3.2" "astronomer-cosmos==1.16.0"

# Venv du projet, construit depuis uv.lock (sans les dépendances de dev)
USER root
COPY pyproject.toml uv.lock /tmp/ecoshop/
RUN cd /tmp/ecoshop \
    && UV_PROJECT_ENVIRONMENT=/opt/ecoshop-venv UV_PYTHON_DOWNLOADS=never \
       uv sync --frozen --no-install-project --no-dev --no-cache \
    && chown -R airflow: /opt/ecoshop-venv \
    && rm -rf /tmp/ecoshop
USER airflow
