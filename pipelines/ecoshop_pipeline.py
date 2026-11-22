"""Pipeline dlt : ingestion du back-office EcoShop dans PostgreSQL (schéma raw_ecoshop).

Usage (depuis la racine du projet) :
    uv run python pipelines/ecoshop_pipeline.py
"""

from datetime import datetime, timezone

import dlt

from fake_data import START_DATE, generate_customers, generate_orders, generate_products


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
    yield from generate_customers(now=datetime.now(timezone.utc))


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
        now=datetime.now(timezone.utc),
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
