"""Pipeline dlt : Demandes de Valeurs Foncières géolocalisées (DVF) -> schéma raw_dvf.

Source : https://files.data.gouv.fr/geo-dvf/ (Etalab, licence ouverte).
Un fichier CSV compressé par année et par département, republié chaque semestre.

Principes :
- années et départements paramétrables dans .dlt/config.toml (section [sources.dvf]) ;
- typage explicite des colonnes (un CSV ne porte aucun type) ;
- incrémental par fichier : un fichier inchangé depuis le dernier run n'est pas retéléchargé ;
- remplacement par partition : si un fichier a été republié, ses anciennes lignes
  sont supprimées puis remplacées (stratégie merge "delete-insert" sur la colonne `fichier`).

Usage (depuis la racine du projet) :
    uv run python pipelines/dvf_pipeline.py
"""

import gzip
import io

import dlt
import pyarrow as pa
import pyarrow.csv as pacsv
from dlt.sources.helpers import requests  # requests avec reprises automatiques

URL_FICHIER = "https://files.data.gouv.fr/geo-dvf/latest/csv/{annee}/departements/{departement}.csv.gz"

# Colonnes non textuelles. Toutes les autres restent du texte, en particulier les
# codes (code_postal, code_commune, id_parcelle...) dont les zéros initiaux comptent.
TYPES_NUMERIQUES = {
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


def lire_csv_dvf(contenu_gz: bytes) -> pa.Table:
    """Décompresse et lit un fichier DVF avec des types explicites."""
    contenu = gzip.decompress(contenu_gz)
    entete = contenu.split(b"\n", 1)[0].decode("utf-8").strip().split(",")
    types = {colonne: TYPES_NUMERIQUES.get(colonne, pa.string()) for colonne in entete}
    return pacsv.read_csv(
        io.BytesIO(contenu),
        convert_options=pacsv.ConvertOptions(column_types=types, strings_can_be_null=True),
    )


@dlt.source(name="dvf", section="dvf")
def dvf_source(
    annees: list[int] = dlt.config.value,
    departements: list[str] = dlt.config.value,
):
    """Les paramètres sont injectés depuis .dlt/config.toml -> [sources.dvf]."""

    @dlt.resource(
        name="mutations",
        write_disposition={"disposition": "merge", "strategy": "delete-insert"},
        merge_key="fichier",
    )
    def mutations():
        # État propre à la ressource, sauvegardé par dlt dans la destination
        fichiers_charges = dlt.current.resource_state().setdefault("fichiers_charges", {})

        for annee in annees:
            for departement in departements:
                fichier = f"{annee}/{departement}"
                url = URL_FICHIER.format(annee=annee, departement=departement)

                # 1. Le fichier a-t-il changé depuis le dernier chargement ?
                entete_http = requests.head(url, allow_redirects=True, timeout=30)
                entete_http.raise_for_status()
                version = entete_http.headers.get("Last-Modified")
                if fichiers_charges.get(fichier) == version:
                    print(f"  {fichier} : inchangé ({version}), ignoré")
                    continue

                # 2. Téléchargement et lecture typée
                reponse = requests.get(url, timeout=120)
                reponse.raise_for_status()
                table = lire_csv_dvf(reponse.content)

                # 3. Colonnes techniques : partition de remplacement et traçabilité.
                #    Déclarées non nullables : `fichier` est la merge_key, que dlt exige non nulle.
                nb_lignes = table.num_rows
                colonnes_techniques = [
                    ("annee", pa.int16(), annee),
                    ("fichier", pa.string(), fichier),
                    ("version_fichier", pa.string(), version),
                ]
                for nom, type_arrow, valeur in colonnes_techniques:
                    table = table.append_column(
                        pa.field(nom, type_arrow, nullable=False),
                        pa.array([valeur] * nb_lignes, type_arrow),
                    )

                print(f"  {fichier} : {nb_lignes} lignes ({version})")
                yield table

                # 4. Mémorisation (persistée uniquement si le chargement réussit)
                fichiers_charges[fichier] = version

    return mutations


def run():
    """Lance le chargement et renvoie le rapport de chargement (LoadInfo)."""
    pipeline = dlt.pipeline(
        pipeline_name="dvf",
        destination="postgres",
        dataset_name="raw_dvf",
    )
    return pipeline.run(dvf_source())


if __name__ == "__main__":
    print(run())
