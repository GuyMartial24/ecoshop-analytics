"""Alertes qualité des données en français sur Slack (#data-alerts).

Règles de rédaction : messages en français, sobres, sans aucun émoji.

Lit les résultats collectés par le package dbt Elementary (schéma `elementary`) pour la
dernière exécution dbt (build ou test) et publie un message en français sur Slack via un
Incoming Webhook. Remplace `edr monitor`, dont les messages ne sont disponibles qu'en anglais.

Variables d'environnement (fichier .env en local) :
    WAREHOUSE_USER, WAREHOUSE_PASSWORD, WAREHOUSE_DB, WAREHOUSE_PORT (ou DBT_HOST / DBT_PORT)
    SLACK_WEBHOOK_URL

Usage (depuis la racine du projet) :
    uv run python scripts/slack_alerts.py            # envoie une alerte s'il y a des anomalies
    uv run python scripts/slack_alerts.py --apercu   # affiche le message sans l'envoyer
    uv run python scripts/slack_alerts.py --toujours # envoie aussi un message si tout est OK
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

import psycopg2
import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

STATUTS = {
    "error": "Erreur",
    "fail": "Échec",
    "warn": "Avertissement",
}

# Libellés français des types de tests (nom court dbt -> libellé)
TYPES_DE_TESTS = {
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


def connexion():
    return psycopg2.connect(
        host=os.environ.get("DBT_HOST", "localhost"),
        port=int(os.environ.get("DBT_PORT", os.environ.get("WAREHOUSE_PORT", "5433"))),
        user=os.environ["WAREHOUSE_USER"],
        password=os.environ["WAREHOUSE_PASSWORD"],
        dbname=os.environ["WAREHOUSE_DB"],
    )


def derniere_execution(curseur):
    """Dernière exécution dbt ayant lancé des tests (build ou test)."""
    curseur.execute(
        """
        select invocation_id, command, generated_at
        from elementary.dbt_invocations
        where command in ('build', 'test')
        order by generated_at desc
        limit 1
        """
    )
    return curseur.fetchone()


def resultats_tests(curseur, invocation_id):
    curseur.execute(
        """
        select status, test_short_name, test_type, schema_name, table_name,
               column_name, failures
        from elementary.elementary_test_results
        where invocation_id = %s
        """,
        (invocation_id,),
    )
    return curseur.fetchall()


def modeles_en_erreur(curseur, invocation_id):
    curseur.execute(
        """
        select name, resource_type, message
        from elementary.dbt_run_results
        where invocation_id = %s and status = 'error'
        """,
        (invocation_id,),
    )
    return curseur.fetchall()


def libelle_test(test_short_name, test_type):
    if test_short_name in TYPES_DE_TESTS:
        return TYPES_DE_TESTS[test_short_name]
    if test_type == "dbt_test" and test_short_name.startswith("assert_"):
        return f"règle métier ({test_short_name})"
    return test_short_name


def construire_message(execution, resultats, erreurs):
    invocation_id, commande, genere_le = execution
    if isinstance(genere_le, str):
        genere_le = datetime.fromisoformat(genere_le)
    date = genere_le.strftime("%d/%m/%Y à %H:%M") + " (UTC)"

    anomalies = [r for r in resultats if r[0] in STATUTS]
    nb = {statut: sum(1 for r in anomalies if r[0] == statut) for statut in STATUTS}
    gravite = "ÉCHEC" if (nb["fail"] or nb["error"] or erreurs) else "AVERTISSEMENT"

    lignes = [
        f"*Contrôle qualité des données EcoShop : {gravite if anomalies or erreurs else 'OK'}*",
        f"Exécution `dbt {commande}` du {date}",
        (
            f"{len(resultats)} tests exécutés : {nb['fail'] + nb['error']} en échec, "
            f"{nb['warn']} en avertissement."
        ),
    ]

    if erreurs:
        lignes.append("")
        lignes.append("*Modèles en erreur*")
        for nom, type_ressource, message in erreurs:
            lignes.append(f"- `{nom}` ({type_ressource}) : {(message or '')[:200]}")

    if anomalies:
        lignes.append("")
        lignes.append("*Tests en anomalie*")
        ordre = {"error": 0, "fail": 1, "warn": 2}
        for statut, nom_court, type_test, schema, table, colonne, echecs in sorted(
            anomalies, key=lambda r: (ordre[r[0]], r[3] or "", r[4] or "")
        ):
            cible = f"{schema}.{table}" + (f".{colonne}" if colonne else "")
            detail = f" : {echecs} ligne(s) en anomalie" if echecs else ""
            lignes.append(
                f"- {STATUTS[statut]} | {libelle_test(nom_court, type_test)} | `{cible}`{detail}"
            )

    lignes.append("")
    lignes.append(
        "Rapport détaillé : `uv run edr report` depuis dbt_project/ "
        "(fichier edr_target/elementary_report.html)."
    )
    return "\n".join(lignes), bool(anomalies or erreurs)


def main() -> int:
    parser = argparse.ArgumentParser(description="Alertes qualité des données en français sur Slack.")
    parser.add_argument("--apercu", action="store_true", help="affiche le message sans l'envoyer")
    parser.add_argument("--toujours", action="store_true", help="envoie un message même si tout est OK")
    args = parser.parse_args()

    load_dotenv(PROJECT_ROOT / ".env")

    with connexion() as conn, conn.cursor() as curseur:
        execution = derniere_execution(curseur)
        if execution is None:
            print("Aucune exécution dbt enregistrée par Elementary.")
            return 0
        resultats = resultats_tests(curseur, execution[0])
        erreurs = modeles_en_erreur(curseur, execution[0])

    message, a_signaler = construire_message(execution, resultats, erreurs)

    if args.apercu:
        print(message)
        return 0
    if not a_signaler and not args.toujours:
        print("Aucune anomalie : pas de message envoyé.")
        return 0

    reponse = requests.post(os.environ["SLACK_WEBHOOK_URL"], json={"text": message}, timeout=30)
    if reponse.status_code != 200:
        print(f"Échec de l'envoi Slack (HTTP {reponse.status_code}) : {reponse.text}", file=sys.stderr)
        return 1
    print("Alerte envoyée sur Slack.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
