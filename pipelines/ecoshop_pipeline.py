"""Ingestion du back-office EcoShop dans le schéma raw_ecoshop.

Lancement : uv run python pipelines/ecoshop_pipeline.py

ECOSHOP_SIMULATED_NOW (date ISO 8601) fixe la date du simulateur.
Utilisée uniquement par replay_history.py.
"""

import os
from datetime import datetime, timezone

import dlt
from fake_data import (
    START_DATE,
    generate_customers,
    generate_orders,
    generate_products,
)


def current_time() -> datetime:
    """Date courante, ou date simulée si ECOSHOP_SIMULATED_NOW existe."""
    simulated_now = os.environ.get("ECOSHOP_SIMULATED_NOW")
    if simulated_now:
        return datetime.fromisoformat(simulated_now)
    return datetime.now(timezone.utc)


@dlt.resource(name="products", write_disposition="replace")
def products():
    yield from generate_products()


@dlt.resource(
    name="customers", write_disposition="merge", primary_key="customer_id"
)
def customers(
    updated_at=dlt.sources.incremental("updated_at", initial_value=START_DATE),
):
    # dlt écarte les clients non modifiés depuis le dernier chargement
    yield from generate_customers(now=current_time())


@dlt.resource(name="orders", write_disposition="merge", primary_key="order_id")
def orders(
    updated_at=dlt.sources.incremental("updated_at", initial_value=START_DATE),
):
    # La dernière valeur chargée est transmise à la source
    yield from generate_orders(
        updated_since=updated_at.last_value,
        now=current_time(),
    )


@dlt.source(name="ecoshop")
def ecoshop_source():
    return products, customers, orders


def run():
    pipeline = dlt.pipeline(
        pipeline_name="ecoshop",
        destination="postgres",
        dataset_name="raw_ecoshop",
    )
    return pipeline.run(ecoshop_source())


if __name__ == "__main__":
    print(run())
