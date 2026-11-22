"""Pipeline dlt : ingestion du back-office EcoShop dans PostgreSQL (schéma raw_ecoshop).

Usage (depuis la racine du projet) :
    uv run python pipelines/ecoshop_pipeline.py

La variable d'environnement ECOSHOP_SIMULATED_NOW (date ISO 8601) permet de faire
tourner le simulateur à une date passée ; elle sert uniquement au rejeu de
l'historique (pipelines/replay_history.py).
"""

import os
from datetime import datetime, timezone

import dlt

from fake_data import START_DATE, generate_customers, generate_orders, generate_products


def current_time() -> datetime:
    """Date de référence du simulateur : maintenant, ou la date simulée si elle est définie."""
    simulated_now = os.environ.get("ECOSHOP_SIMULATED_NOW")
    if simulated_now:
        return datetime.fromisoformat(simulated_now)
    return datetime.now(timezone.utc)


@dlt.resource(name="products", write_disposition="replace")
def products():
    """Catalogue produits : petit référentiel renvoyé en entier -> on remplace la table."""
    yield from generate_products()


@dlt.resource(name="customers", write_disposition="merge", primary_key="customer_id")
def customers(
    updated_at=dlt.sources.incremental("updated_at", initial_value=START_DATE),
):
    """Clients : upsert sur customer_id.

    La source renvoie tous les clients ; dlt écarte lui-même ceux dont
    updated_at n'a pas bougé depuis le dernier chargement (filtrage côté dlt).
    """
    yield from generate_customers(now=current_time())


@dlt.resource(name="orders", write_disposition="merge", primary_key="order_id")
def orders(
    updated_at=dlt.sources.incremental("updated_at", initial_value=START_DATE),
):
    """Commandes : upsert sur order_id.

    On transmet la dernière valeur chargée à la source (filtrage côté source),
    comme on le ferait avec une API : GET /orders?updated_since=<last_value>.
    """
    yield from generate_orders(
        updated_since=updated_at.last_value,
        now=current_time(),
    )


@dlt.source(name="ecoshop")
def ecoshop_source():
    """Regroupe les tables issues du même système source (le back-office)."""
    return products, customers, orders


def run():
    """Lance le chargement et renvoie le rapport de chargement (LoadInfo)."""
    pipeline = dlt.pipeline(
        pipeline_name="ecoshop",      # nom du pipeline (et de son état local)
        destination="postgres",       # identifiants lus dans .dlt/secrets.toml
        dataset_name="raw_ecoshop",   # schéma PostgreSQL de destination (Bronze)
    )
    return pipeline.run(ecoshop_source())


if __name__ == "__main__":
    print(run())
