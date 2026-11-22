"""Rejeu de l'historique du back-office pour constituer l'historique SCD2 des clients.

Un snapshot dbt ne capture que les changements qu'il observe au moment où il tourne.
Mis en place après coup, il ne connaîtrait que l'état actuel des clients. Le simulateur
étant déterministe, on peut reconstituer le passé : on repart d'un schéma brut vide,
puis on avance dans le temps mois par mois en enchaînant ingestion dlt et dbt snapshot.

ATTENTION : ce script supprime et recharge le schéma raw_ecoshop ainsi que le snapshot
snap_customers. Il est réservé à l'environnement de développement.

Usage (depuis la racine du projet) :
    uv run python pipelines/replay_history.py
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import dlt
from dbt.cli.main import dbtRunner
from dotenv import load_dotenv

import ecoshop_pipeline
from fake_data import START_DATE

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DBT_DIR = PROJECT_ROOT / "dbt_project"


def month_starts(start: datetime, end: datetime):
    """Premier jour de chaque mois entre start (exclu) et end (exclu)."""
    year, month = start.year, start.month
    while True:
        month += 1
        if month > 12:
            year, month = year + 1, 1
        point = datetime(year, month, 1, tzinfo=timezone.utc)
        if point >= end:
            return
        yield point


def reset_raw_ecoshop() -> None:
    """Supprime le schéma raw_ecoshop, l'état du pipeline et le snapshot existant."""
    pipeline = dlt.pipeline(pipeline_name="ecoshop", destination="postgres", dataset_name="raw_ecoshop")
    with pipeline.sql_client() as client:
        client.execute_sql("drop table if exists snapshots.snap_customers")
        if client.has_dataset():
            client.drop_dataset()
    pipeline.drop()  # état local du pipeline


def run_dbt(args: list[str]) -> None:
    result = dbtRunner().invoke(
        args + ["--project-dir", str(DBT_DIR), "--profiles-dir", str(DBT_DIR), "--quiet"]
    )
    if not result.success:
        raise RuntimeError(f"Échec de la commande dbt {' '.join(args)}")


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")  # identifiants lus par profiles.yml
    now = datetime.now(timezone.utc)

    print("Réinitialisation de raw_ecoshop et du snapshot...")
    reset_raw_ecoshop()

    # Les vues staging doivent exister pour que le snapshot puisse les lire
    points_in_time = list(month_starts(START_DATE, now)) + [None]  # None = maintenant
    for index, point in enumerate(points_in_time, start=1):
        if point is None:
            os.environ.pop("ECOSHOP_SIMULATED_NOW", None)
            label = "maintenant"
        else:
            os.environ["ECOSHOP_SIMULATED_NOW"] = point.isoformat()
            label = point.strftime("%Y-%m-%d")

        ecoshop_pipeline.run().raise_on_failed_jobs()
        if index == 1:
            run_dbt(["run", "--select", "stg_ecoshop__customers"])
        run_dbt(["snapshot", "--select", "snap_customers"])
        print(f"  [{index:02d}/{len(points_in_time)}] {label} : ingestion + snapshot OK")

    print("Rejeu terminé.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
