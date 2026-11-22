"""Reconstruit l'historique SCD2 des clients en rejouant la source.

Repart d'un schéma raw_ecoshop vide puis, pour chaque début de mois depuis
START_DATE, lance l'ingestion puis `dbt snapshot`.

Supprime raw_ecoshop et snapshots.snap_customers : développement uniquement.
Lancement : uv run python pipelines/replay_history.py
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import dlt
import ecoshop_pipeline
from dbt.cli.main import dbtRunner
from dotenv import load_dotenv
from fake_data import START_DATE

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DBT_DIR = PROJECT_ROOT / "dbt_project"


def month_starts(start: datetime, end: datetime):
    """Premier jour de chaque mois entre start et end (bornes exclues)."""
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
    pipeline = dlt.pipeline(
        pipeline_name="ecoshop",
        destination="postgres",
        dataset_name="raw_ecoshop",
    )
    with pipeline.sql_client() as client:
        client.execute_sql("drop table if exists snapshots.snap_customers")
        if client.has_dataset():
            client.drop_dataset()
    pipeline.drop()


def run_dbt(args: list[str]) -> None:
    dirs = ["--project-dir", str(DBT_DIR), "--profiles-dir", str(DBT_DIR)]
    result = dbtRunner().invoke(args + dirs + ["--quiet"])
    if not result.success:
        raise RuntimeError(f"Échec de la commande dbt {' '.join(args)}")


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    now = datetime.now(timezone.utc)

    print("Réinitialisation de raw_ecoshop et du snapshot...")
    reset_raw_ecoshop()

    # None = date réelle, pour le dernier passage
    points_in_time = list(month_starts(START_DATE, now)) + [None]
    total = len(points_in_time)
    for index, point in enumerate(points_in_time, start=1):
        if point is None:
            os.environ.pop("ECOSHOP_SIMULATED_NOW", None)
            label = "maintenant"
        else:
            os.environ["ECOSHOP_SIMULATED_NOW"] = point.isoformat()
            label = point.strftime("%Y-%m-%d")

        ecoshop_pipeline.run().raise_on_failed_jobs()
        if index == 1:
            # Le snapshot lit cette vue
            run_dbt(["run", "--select", "stg_ecoshop__customers"])
        run_dbt(["snapshot", "--select", "snap_customers"])
        print(f"  [{index:02d}/{total}] {label} : ingestion + snapshot OK")

    print("Rejeu terminé.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
