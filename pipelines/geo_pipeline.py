"""Ingestion du référentiel géographique (API Géo) dans le schéma raw_geo.

Source : https://geo.api.gouv.fr
Lancement : uv run python pipelines/geo_pipeline.py
"""

import dlt
from dlt.sources.rest_api import rest_api_source

COMMUNE_FIELDS = (
    "nom,code,type,codesPostaux,centre,surface,population,"
    "codeDepartement,codeRegion"
)
# Arrondissements inclus : DVF utilise leurs codes INSEE
COMMUNE_TYPES = "commune-actuelle,arrondissement-municipal"


def flatten_centre(commune: dict) -> dict:
    """Remplace le point GeoJSON `centre` par longitude et latitude."""
    centre = commune.pop("centre", None) or {}
    coordinates = centre.get("coordinates") or [None, None]
    commune["longitude"], commune["latitude"] = coordinates
    return commune


def geo_source():
    return rest_api_source(
        {
            "client": {"base_url": "https://geo.api.gouv.fr/"},
            "resource_defaults": {
                "write_disposition": "replace",
                "endpoint": {"paginator": "single_page"},
            },
            "resources": [
                {
                    "name": "regions",
                    "primary_key": "code",
                    "endpoint": {"path": "regions"},
                },
                {
                    "name": "departements",
                    "primary_key": "code",
                    "endpoint": {"path": "departements"},
                },
                {
                    "name": "communes",
                    "primary_key": "code",
                    "endpoint": {
                        "path": "communes",
                        "params": {
                            "fields": COMMUNE_FIELDS,
                            "type": COMMUNE_TYPES,
                        },
                    },
                    "processing_steps": [{"map": flatten_centre}],
                },
            ],
        },
        name="geo",
    )


def run():
    pipeline = dlt.pipeline(
        pipeline_name="geo",
        destination="postgres",
        dataset_name="raw_geo",
    )
    return pipeline.run(geo_source())


if __name__ == "__main__":
    print(run())
