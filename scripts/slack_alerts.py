"""Alertes qualité des données sur Slack (#data-alerts), en français.

Lit les résultats enregistrés par Elementary (schéma `elementary`) et les
publie via le webhook SLACK_WEBHOOK_URL.

Lancement :
    uv run python scripts/slack_alerts.py              # si anomalies
    uv run python scripts/slack_alerts.py --apercu     # sans envoi
    uv run python scripts/slack_alerts.py --toujours   # même si tout est OK
    uv run python scripts/slack_alerts.py --depuis 2026-11-22T02:00:00+00:00
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

STATUS_LABELS = {
    "error": "Erreur",
    "fail": "Échec",
    "warn": "Avertissement",
}

TEST_LABELS = {
    "not_null": "valeurs manquantes",
    "unique": "doublons",
    "relationships": "intégrité référentielle",
    "accepted_values": "valeurs non autorisées",
    "unique_combination_of_columns": "doublons sur clé composite",
    "expression_is_true": "règle de cohérence",
    "accepted_range": "valeurs hors plage",
    "positive_value": "valeurs négatives ou nulles",
    "volume_anomalies": "anomalie de volume",
    "freshness_anomalies": "anomalie de fraîcheur",
    "schema_changes": "changement de schéma",
}


def connect():
    port = os.environ.get("DBT_PORT", os.environ.get("WAREHOUSE_PORT", "5433"))
    return psycopg2.connect(
        host=os.environ.get("DBT_HOST", "localhost"),
        port=int(port),
        user=os.environ["WAREHOUSE_USER"],
        password=os.environ["WAREHOUSE_PASSWORD"],
        dbname=os.environ["WAREHOUSE_DB"],
    )


def last_invocation(cursor):
    """Dernière exécution dbt build ou test."""
    cursor.execute(
        """
        select invocation_id, command, generated_at
        from elementary.dbt_invocations
        where command in ('build', 'test')
        order by generated_at desc
        limit 1
        """
    )
    return cursor.fetchone()


def test_results(cursor, invocation_id=None, since=None):
    """Résultats d'une exécution, ou de toutes les exécutions depuis `since`.

    `since` sert pour Airflow : Cosmos lance une exécution dbt par tâche.
    """
    if since is None:
        condition, value = "invocation_id = %s", invocation_id
    else:
        condition, value = "detected_at >= %s", since
    cursor.execute(
        f"""
        select status, test_short_name, test_type, schema_name,
               table_name, column_name, failures
        from elementary.elementary_test_results
        where {condition}
        """,
        (value,),
    )
    return cursor.fetchall()


def failed_models(cursor, invocation_id=None, since=None):
    if since is None:
        condition, value = "invocation_id = %s", invocation_id
    else:
        condition, value = "generated_at::timestamp >= %s", since
    cursor.execute(
        f"""
        select name, resource_type, message
        from elementary.dbt_run_results
        where {condition} and status = 'error'
        """,
        (value,),
    )
    return cursor.fetchall()


def test_label(short_name, test_type):
    if short_name in TEST_LABELS:
        return TEST_LABELS[short_name]
    if test_type == "dbt_test" and short_name.startswith("assert_"):
        return f"règle métier ({short_name})"
    return short_name


def build_message(context_line, results, errors):
    """Renvoie (message, True si quelque chose est à signaler)."""
    issues = [r for r in results if r[0] in STATUS_LABELS]
    counts = {
        status: sum(1 for r in issues if r[0] == status)
        for status in STATUS_LABELS
    }
    nb_failed = counts["fail"] + counts["error"]

    if nb_failed or errors:
        level = "ÉCHEC"
    elif issues:
        level = "AVERTISSEMENT"
    else:
        level = "OK"

    lines = [
        f"*Contrôle qualité des données EcoShop : {level}*",
        context_line,
        f"{len(results)} tests exécutés : {nb_failed} en échec, "
        f"{counts['warn']} en avertissement.",
    ]

    if errors:
        lines += ["", "*Modèles en erreur*"]
        for name, resource_type, message in errors:
            lines.append(
                f"- `{name}` ({resource_type}) : {(message or '')[:200]}"
            )

    if issues:
        lines += ["", "*Tests en anomalie*"]
        order = {"error": 0, "fail": 1, "warn": 2}
        issues.sort(key=lambda r: (order[r[0]], r[3] or "", r[4] or ""))
        for status, short_name, test_type, schema, table, column, nb in issues:
            target = f"{schema}.{table}" + (f".{column}" if column else "")
            detail = f" : {nb} ligne(s) en anomalie" if nb else ""
            label = test_label(short_name, test_type)
            lines.append(
                f"- {STATUS_LABELS[status]} | {label} | `{target}`{detail}"
            )

    lines += [
        "",
        "Rapport détaillé : `uv run edr report` depuis dbt_project/ "
        "(fichier edr_target/elementary_report.html).",
    ]
    return "\n".join(lines), bool(issues or errors)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Alertes qualité des données sur Slack."
    )
    parser.add_argument(
        "--apercu", action="store_true", help="affiche le message sans envoi"
    )
    parser.add_argument(
        "--toujours", action="store_true", help="envoie même si tout est OK"
    )
    parser.add_argument(
        "--depuis", help="date ISO 8601 : exécutions depuis cette date"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    # Les variables déjà définies (conteneur Airflow) restent prioritaires
    load_dotenv(PROJECT_ROOT / ".env")

    with connect() as conn, conn.cursor() as cursor:
        if args.depuis:
            # Elementary stocke des dates UTC sans fuseau
            since = datetime.fromisoformat(args.depuis)
            since = since.astimezone(timezone.utc).replace(tzinfo=None)
            results = test_results(cursor, since=since)
            errors = failed_models(cursor, since=since)
            context_line = (
                f"Pipeline quotidien démarré le {since:%d/%m/%Y à %H:%M} (UTC)"
            )
        else:
            invocation = last_invocation(cursor)
            if invocation is None:
                print("Aucune exécution dbt enregistrée par Elementary.")
                return 0
            invocation_id, command, generated_at = invocation
            if isinstance(generated_at, str):
                generated_at = datetime.fromisoformat(generated_at)
            results = test_results(cursor, invocation_id=invocation_id)
            errors = failed_models(cursor, invocation_id=invocation_id)
            context_line = (
                f"Exécution `dbt {command}` du "
                f"{generated_at:%d/%m/%Y à %H:%M} (UTC)"
            )

    message, has_issues = build_message(context_line, results, errors)

    if args.apercu:
        print(message)
        return 0
    if not has_issues and not args.toujours:
        print("Aucune anomalie : pas de message envoyé.")
        return 0

    response = requests.post(
        os.environ["SLACK_WEBHOOK_URL"], json={"text": message}, timeout=30
    )
    if response.status_code != 200:
        print(
            f"Échec de l'envoi Slack (HTTP {response.status_code}) : "
            f"{response.text}",
            file=sys.stderr,
        )
        return 1
    print("Alerte envoyée sur Slack.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
