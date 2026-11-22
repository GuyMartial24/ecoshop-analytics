"""Lance les trois pipelines d'ingestion dlt (couche Bronze) les uns après les autres.

C'est ce point d'entrée unique qu'appellera l'orchestrateur (Airflow, étape 6).
Le code de sortie est 1 si au moins un pipeline échoue, pour que l'échec soit
visible par l'orchestrateur ou la CI.

Usage (depuis la racine du projet) :
    uv run python pipelines/run_all.py
"""

import sys
import time

import dvf_pipeline
import ecoshop_pipeline
import geo_pipeline

# Ordre : référentiel géographique, puis sources métier
PIPELINES = {
    "geo": geo_pipeline.run,
    "ecoshop": ecoshop_pipeline.run,
    "dvf": dvf_pipeline.run,
}


def main() -> int:
    echecs = []
    for nom, lancer in PIPELINES.items():
        debut = time.perf_counter()
        print(f"=== {nom} ===")
        try:
            load_info = lancer()
            load_info.raise_on_failed_jobs()  # échoue si une table n'a pas été chargée
            print(load_info)
            print(f"--> {nom} : OK en {time.perf_counter() - debut:.1f} s\n")
        except Exception as erreur:  # on continue avec les autres sources
            echecs.append(nom)
            print(f"--> {nom} : ÉCHEC ({erreur})\n", file=sys.stderr)

    if echecs:
        print(f"Pipelines en échec : {', '.join(echecs)}", file=sys.stderr)
        return 1
    print("Tous les pipelines ont réussi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
