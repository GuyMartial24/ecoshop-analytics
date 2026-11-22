"""
### Pipeline quotidien EcoShop

1. `ingestion_dlt` : chargement des trois sources avec dlt.
2. `fraicheur_sources` : `dbt source freshness`.
3. `transformations_dbt` : projet dbt rendu par Cosmos (une tâche par
   modèle, suivie de ses tests).
4. `alertes_qualite_slack` : synthèse qualité sur Slack, même en cas
   d'échec d'une étape précédente.

Une tâche en échec envoie aussi une alerte Slack.
"""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG
from cosmos import (
    DbtTaskGroup,
    ExecutionConfig,
    LoadMode,
    ProfileConfig,
    ProjectConfig,
    RenderConfig,
)
from cosmos.constants import InvocationMode

ECOSHOP_HOME = Path(os.environ.get("ECOSHOP_HOME", "/opt/ecoshop"))
VENV_BIN = Path(os.environ.get("ECOSHOP_VENV", "/opt/ecoshop-venv")) / "bin"
DBT_PROJECT_DIR = ECOSHOP_HOME / "dbt_project"
DBT_EXECUTABLE = str(VENV_BIN / "dbt")
DBT_TARGET = os.environ.get("DBT_TARGET", "dev")


def notify_task_failure(context) -> None:
    """Envoie un message Slack quand une tâche échoue."""
    webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook:
        return
    ti = context["ti"]
    started = "inconnue"
    if ti.start_date:
        started = ti.start_date.strftime("%d/%m/%Y à %H:%M")
    message = "\n".join(
        [
            "*Échec du pipeline EcoShop*",
            f"Tâche : `{ti.task_id}` (tentative {ti.try_number})",
            f"DAG : `{ti.dag_id}`, exécution `{context['run_id']}`",
            f"Début de la tâche : {started} (UTC)",
            "Consulter le journal de la tâche dans l'interface Airflow.",
        ]
    )
    try:
        requests.post(webhook, json={"text": message}, timeout=30)
    except requests.RequestException:
        pass


with DAG(
    dag_id="ecoshop_quotidien",
    description="Ingestion dlt, transformations dbt et alertes qualité",
    doc_md=__doc__,
    schedule="0 2 * * *",
    start_date=datetime(2026, 11, 1, tzinfo=timezone.utc),
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "ecoshop",
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
        "on_failure_callback": notify_task_failure,
    },
    tags=["ecoshop", "dlt", "dbt", "cosmos"],
):
    ingestion = BashOperator(
        task_id="ingestion_dlt",
        bash_command=(
            f"cd {ECOSHOP_HOME} && {VENV_BIN}/python pipelines/run_all.py"
        ),
        retries=2,
    )

    freshness = BashOperator(
        task_id="fraicheur_sources",
        bash_command=(
            f"cd {DBT_PROJECT_DIR} && "
            f"{DBT_EXECUTABLE} source freshness --target {DBT_TARGET}"
        ),
    )

    transformations = DbtTaskGroup(
        group_id="transformations_dbt",
        project_config=ProjectConfig(DBT_PROJECT_DIR, install_dbt_deps=False),
        profile_config=ProfileConfig(
            profile_name="ecoshop",
            target_name=DBT_TARGET,
            profiles_yml_filepath=DBT_PROJECT_DIR / "profiles.yml",
        ),
        # dbt est lancé depuis le venv du projet, pas celui d'Airflow
        execution_config=ExecutionConfig(
            dbt_executable_path=DBT_EXECUTABLE,
            invocation_mode=InvocationMode.SUBPROCESS,
        ),
        render_config=RenderConfig(
            load_method=LoadMode.DBT_LS,
            dbt_executable_path=DBT_EXECUTABLE,
            invocation_mode=InvocationMode.SUBPROCESS,
            exclude=["package:elementary"],
            # Tests sur plusieurs modèles lancés après tous leurs parents
            should_detach_multiple_parents_tests=True,
        ),
        # Métadonnées Elementary envoyées une fois, par fraicheur_sources
        operator_args={"vars": {"disable_dbt_artifacts_autoupload": True}},
        default_args={"retries": 0},
    )

    alerts = BashOperator(
        task_id="alertes_qualite_slack",
        bash_command=(
            f"cd {ECOSHOP_HOME} && "
            f"{VENV_BIN}/python scripts/slack_alerts.py "
            "--depuis '{{ dag_run.start_date.isoformat() }}'"
        ),
        trigger_rule="all_done",
    )

    ingestion >> freshness >> transformations >> alerts
