"""Ingestion des Demandes de Valeurs Foncières (DVF) dans le schéma raw_dvf.

Source : https://files.data.gouv.fr/geo-dvf/ (un fichier par année et par
département, republié chaque semestre).
Années et départements : section [sources.dvf] de .dlt/config.toml.

Lancement : uv run python pipelines/dvf_pipeline.py
"""

import gzip
import io

import dlt
import pyarrow as pa
import pyarrow.csv as pacsv
from dlt.sources.helpers import requests

FILE_URL = (
    "https://files.data.gouv.fr/geo-dvf/latest/csv/"
    "{year}/departements/{department}.csv.gz"
)

# Colonnes typées ; les autres restent en texte (codes avec zéros initiaux)
NUMERIC_TYPES = {
    "date_mutation": pa.date32(),
    "valeur_fonciere": pa.float64(),
    "lot1_surface_carrez": pa.float64(),
    "lot2_surface_carrez": pa.float64(),
    "lot3_surface_carrez": pa.float64(),
    "lot4_surface_carrez": pa.float64(),
    "lot5_surface_carrez": pa.float64(),
    "nombre_lots": pa.int64(),
    "surface_reelle_bati": pa.float64(),
    "nombre_pieces_principales": pa.int64(),
    "surface_terrain": pa.float64(),
    "longitude": pa.float64(),
    "latitude": pa.float64(),
}


def read_dvf_csv(gz_content: bytes) -> pa.Table:
    """Décompresse et lit un fichier DVF avec les types attendus."""
    content = gzip.decompress(gz_content)
    header = content.split(b"\n", 1)[0].decode("utf-8").strip().split(",")
    types = {col: NUMERIC_TYPES.get(col, pa.string()) for col in header}
    return pacsv.read_csv(
        io.BytesIO(content),
        convert_options=pacsv.ConvertOptions(
            column_types=types, strings_can_be_null=True
        ),
    )


@dlt.source(name="dvf", section="dvf")
def dvf_source(
    annees: list[int] = dlt.config.value,
    departements: list[str] = dlt.config.value,
):
    @dlt.resource(
        name="mutations",
        write_disposition={
            "disposition": "merge",
            "strategy": "delete-insert",
        },
        merge_key="fichier",
    )
    def mutations():
        # Version (Last-Modified) de chaque fichier déjà chargé
        loaded_files = dlt.current.resource_state().setdefault(
            "fichiers_charges", {}
        )

        for year in annees:
            for department in departements:
                file_key = f"{year}/{department}"
                url = FILE_URL.format(year=year, department=department)

                head = requests.head(url, allow_redirects=True, timeout=30)
                head.raise_for_status()
                version = head.headers.get("Last-Modified")
                if loaded_files.get(file_key) == version:
                    print(f"  {file_key} : inchangé ({version}), ignoré")
                    continue

                response = requests.get(url, timeout=120)
                response.raise_for_status()
                table = read_dvf_csv(response.content)

                # `fichier` est la merge_key : non nullable
                nb_rows = table.num_rows
                extra_columns = [
                    ("annee", pa.int16(), year),
                    ("fichier", pa.string(), file_key),
                    ("version_fichier", pa.string(), version),
                ]
                for name, arrow_type, value in extra_columns:
                    table = table.append_column(
                        pa.field(name, arrow_type, nullable=False),
                        pa.array([value] * nb_rows, arrow_type),
                    )

                print(f"  {file_key} : {nb_rows} lignes ({version})")
                yield table

                loaded_files[file_key] = version

    return mutations


def run():
    pipeline = dlt.pipeline(
        pipeline_name="dvf",
        destination="postgres",
        dataset_name="raw_dvf",
    )
    return pipeline.run(dvf_source())


if __name__ == "__main__":
    print(run())
