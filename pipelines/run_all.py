"""Lance les trois pipelines d'ingestion à la suite.

Code de sortie 1 si au moins un pipeline échoue.
Lancement : uv run python pipelines/run_all.py
"""

import sys
import time

import dvf_pipeline
import ecoshop_pipeline
import geo_pipeline

PIPELINES = {
    "geo": geo_pipeline.run,
    "ecoshop": ecoshop_pipeline.run,
    "dvf": dvf_pipeline.run,
}


def main() -> int:
    failed = []
    for name, run in PIPELINES.items():
        start = time.perf_counter()
        print(f"=== {name} ===")
        try:
            load_info = run()
            load_info.raise_on_failed_jobs()
            print(load_info)
            duration = time.perf_counter() - start
            print(f"--> {name} : OK en {duration:.1f} s\n")
        except Exception as error:
            failed.append(name)
            print(f"--> {name} : ÉCHEC ({error})\n", file=sys.stderr)

    if failed:
        print(f"Pipelines en échec : {', '.join(failed)}", file=sys.stderr)
        return 1
    print("Tous les pipelines ont réussi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
