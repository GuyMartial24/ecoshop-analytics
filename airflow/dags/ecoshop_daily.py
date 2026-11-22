"""
### Pipeline quotidien EcoShop

1. **ingestion_dlt** : chargement des trois sources (API Géo, back-office, DVF) avec dlt.
2. **fraicheur_sources** : contrôle de fraîcheur des sources (`dbt source freshness`).
3. **transformations_dbt** : projet dbt rendu par Cosmos, une tâche par seed, modèle et
   snapshot, chacune suivie de ses tests.
4. **alertes_qualite_slack** : synthèse de la qualité des données publiée sur Slack,
   exécutée même si une étape précédente a échoué.

Toute tâche en échec déclenche aussi une alerte Slack. Les messages Slack sont rédigés
en français, sans émoji.
"""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG
from cosmos import DbtTaskGroup, ExecutionConfig, LoadMode, ProfileConfig, ProjectConfig, RenderConfig
from cosmos.constants import InvocationMode

ECOSHOP_HOME = Path(os.environ.get("ECOSHOP_HOME", "/opt/ecoshop"))
VENV_BIN = Path(os.environ.get("ECOSHOP_VENV", "/opt/ecoshop-venv")) / "bin"
DBT_PROJECT_DIR = ECOSHOP_HOME / "dbt_project"
DBT_EXECUTABLE = str(VENV_BIN / "dbt")
DBT_TARGET = os.environ.get("DBT_TARGET", "dev")


def alerte_echec_tache(context) -> None:
    """Callback d'échec : publie un message en français, sans émoji, sur Slack."""
    webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook:
        return
    ti = context["ti"]
    debut = ti.start_date.strftime("%d/%m/%Y à %H:%M") if ti.start_date else "inconnue"
    message = "\n".join(
        [
            "*Échec du pipeline EcoShop*",
            f"Tâche : `{ti.task_id}` (tentative {ti.try_number})",
            f"DAG : `{ti.dag_id}`, exécution `{context['run_id']}`",
            f"Début de la tâche : {debut} (UTC)",
            "Consulter le journal de la tâche dans l'interface Airflow.",
        ]
    )
    try:
        requests.post(webhook, json={"text": message}, timeout=30)
    except requests.RequestException:
        pass  # une alerte qui échoue ne doit pas masquer l'erreur d'origine


with DAG(
    dag_id="ecoshop_quotidien",
    description="Ingestion dlt, transformations dbt (Cosmos) et alertes qualité en français",
    doc_md=__doc__,
    schedule="0 2 * * *",  # chaque nuit à 2 h (UTC), en dehors des heures de charge du VPS
    start_date=datetime(2026, 11, 1, tzinfo=timezone.utc),
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "ecoshop",
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
        "on_failure_callback": alerte_echec_tache,
    },
    tags=["ecoshop", "dlt", "dbt", "cosmos"],
):

    ingestion = BashOperator(
        task_id="ingestion_dlt",
        bash_command=f"cd {ECOSHOP_HOME} && {VENV_BIN}/python pipelines/run_all.py",
        retries=2,  # les sources externes (API Géo, data.gouv.fr) peuvent être indisponibles
    )

    fraicheur = BashOperator(
        task_id="fraicheur_sources",
        bash_command=f"cd {DBT_PROJECT_DIR} && {DBT_EXECUTABLE} source freshness --target {DBT_TARGET}",
    )

    transformations = DbtTaskGroup(
        group_id="transformations_dbt",
        # dbt_packages/ est déjà présent : pas de `dbt deps` avant chaque tâche
        project_config=ProjectConfig(DBT_PROJECT_DIR, install_dbt_deps=False),
        profile_config=ProfileConfig(
            profile_name="ecoshop",
            target_name=DBT_TARGET,
            profiles_yml_filepath=DBT_PROJECT_DIR / "profiles.yml",
        ),
        # dbt est lancé en sous-processus depuis l'environnement isolé du projet,
        # et non importé dans l'environnement d'Airflow (pas de conflit de dépendances)
        execution_config=ExecutionConfig(
            dbt_executable_path=DBT_EXECUTABLE,
            invocation_mode=InvocationMode.SUBPROCESS,
        ),
        # Rendu du DAG : `dbt ls` (lui aussi en sous-processus) liste les nœuds du projet
        render_config=RenderConfig(
            load_method=LoadMode.DBT_LS,
            dbt_executable_path=DBT_EXECUTABLE,
            invocation_mode=InvocationMode.SUBPROCESS,
            # Les modèles internes d'Elementary sont créés une fois pour toutes
            exclude=["package:elementary"],
            # Un test portant sur plusieurs modèles (ex. relationships) devient une tâche
            # à part, lancée quand tous ses modèles sont construits. Sinon, il pourrait
            # s'exécuter alors qu'un modèle en aval n'est pas encore reconstruit.
            should_detach_multiple_parents_tests=True,
        ),
        # Elementary : les métadonnées du projet (modèles, tests...) sont envoyées une
        # seule fois par run, par la tâche fraicheur_sources. Chaque tâche Cosmos
        # n'enregistre plus que ses propres résultats (environ 30 s gagnées par tâche).
        operator_args={"vars": {"disable_dbt_artifacts_autoupload": True}},
        # Un test en échec ne doit pas être relancé : le résultat serait le même
        default_args={"retries": 0},
    )

    alertes = BashOperator(
        task_id="alertes_qualite_slack",
        bash_command=(
            f"cd {ECOSHOP_HOME} && {VENV_BIN}/python scripts/slack_alerts.py "
            "--depuis '{{ dag_run.start_date.isoformat() }}'"
        ),
        trigger_rule="all_done",  # s'exécute même si une étape précédente a échoué
    )

    ingestion >> fraicheur >> transformations >> alertes
