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

# Node.js et CLI Lightdash, pour déployer la couche sémantique et les
# dashboards depuis le serveur (la CLI a besoin de dbt, présent dans le venv)
COPY --from=node:24.22.1-trixie-slim /usr/local/bin/node /usr/local/bin/node
COPY --from=node:24.22.1-trixie-slim /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && npm install -g --no-fund --no-audit @lightdash/cli@3.361.0
USER airflow
