"""Pipeline dlt : référentiel géographique officiel (API Géo) -> schéma raw_geo.

Source : https://geo.api.gouv.fr (API publique de l'État, sans authentification).
Ce référentiel sert à géolocaliser les clients (code postal) et les ventes DVF
(code commune INSEE) pour la cartographie Lightdash.

Usage (depuis la racine du projet) :
    uv run python pipelines/geo_pipeline.py
"""

import dlt
from dlt.sources.rest_api import rest_api_source

# Champs demandés à l'API (par défaut, elle ne renvoie pas les coordonnées)
CHAMPS_COMMUNE = "nom,code,type,codesPostaux,centre,surface,population,codeDepartement,codeRegion"


def aplatir_centre(commune: dict) -> dict:
    """Transforme le point GeoJSON `centre` en deux colonnes longitude / latitude.

    Sans cette étape, dlt créerait une table enfant pour la liste `coordinates`,
    peu pratique à exploiter dans dbt et Lightdash.
    """
    centre = commune.pop("centre", None) or {}
    coordonnees = centre.get("coordinates") or [None, None]
    commune["longitude"], commune["latitude"] = coordonnees[0], coordonnees[1]
    return commune


def geo_source():
    """Source déclarative : on décrit l'API, dlt se charge des appels HTTP."""
    return rest_api_source(
        {
            "client": {"base_url": "https://geo.api.gouv.fr/"},
            "resource_defaults": {
                # Référentiel complet renvoyé à chaque appel -> on remplace les tables
                "write_disposition": "replace",
                # L'API renvoie toutes les lignes en une seule réponse (pas de pagination)
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
                            "fields": CHAMPS_COMMUNE,
                            # Les arrondissements (Paris, Lyon, Marseille) sont nécessaires
                            # car DVF utilise leurs codes INSEE (ex. 75111 = Paris 11e)
                            "type": "commune-actuelle,arrondissement-municipal",
                        },
                    },
                    "processing_steps": [{"map": aplatir_centre}],
                },
            ],
        },
        name="geo",
    )


def run():
    """Lance le chargement et renvoie le rapport de chargement (LoadInfo)."""
    pipeline = dlt.pipeline(
        pipeline_name="geo",
        destination="postgres",
        dataset_name="raw_geo",
    )
    return pipeline.run(geo_source())


if __name__ == "__main__":
    print(run())
