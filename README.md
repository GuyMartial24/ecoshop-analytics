# EcoShop Analytics
> Plateforme analytique e-commerce & immobilière (DVF) — dlt · dbt · PostgreSQL · Lightdash

## Objectif

Projet d'Analytics Engineering de bout en bout : ingestion de trois sources (un back-office
e-commerce simulé, le référentiel géographique officiel et les transactions immobilières
réelles DVF), transformation avec dbt et restitution dans des dashboards Lightdash.

## Architecture

```
[Back-office simulé]   [API Géo]            [DVF data.gouv.fr]
   (Faker)          (geo.api.gouv.fr)      (CSV géolocalisés)
        └──────────────── dlt ─────────────────┘
                           ▼
┌──────────────── PostgreSQL (Docker) ────────────────┐
│ raw_ecoshop · raw_geo · raw_dvf   (Bronze, dlt)     │
│ seeds · staging · intermediate    (Silver, dbt)     │
│ marts                             (Gold, dbt)       │
└──────────────────────────┬──────────────────────────┘
                           ▼
                Lightdash (Docker) → dashboards
```

## Stack technique

| Rôle | Outil |
|---|---|
| Ingestion | dlt (data load tool) |
| Entrepôt | PostgreSQL 16 |
| Transformation | dbt Core 1.12 (adaptateur PostgreSQL) |
| BI | Lightdash (+ stockage S3 SeaweedFS en local) |
| Orchestration | Airflow 3.3.2 + Astronomer Cosmos 1.16 |
| Infra | Docker Compose, GitHub Actions, VPS |

## Sources de données

| Source | Type | Schéma | Stratégie de chargement |
|---|---|---|---|
| Back-office EcoShop | Simulée (Faker, déterministe et évolutive) | `raw_ecoshop` | `merge` incrémental sur `updated_at` (clients, commandes), `replace` (produits) |
| [API Géo](https://geo.api.gouv.fr) | API REST publique | `raw_geo` | `replace` (référentiel complet) |
| [DVF géolocalisées](https://files.data.gouv.fr/geo-dvf/) | Fichiers CSV Open Data | `raw_dvf` | Incrémental par fichier (`Last-Modified`) + remplacement par partition (`delete-insert`) |

Les années et départements DVF se règlent dans `.dlt/config.toml` (section `[sources.dvf]`).

## Démarrage rapide

Prérequis : Docker Desktop, Python 3.12 et [uv](https://docs.astral.sh/uv/).

```bash
# 1. Variables d'environnement (puis remplacer les valeurs "change_me")
cp .env.example .env

# 2. Stack locale : entrepôt PostgreSQL, Lightdash et son stockage S3
docker compose up -d

# 3. Dépendances Python
uv sync

# 4. Identifiants dlt : créer .dlt/secrets.toml (non versionné)
#    [destination.postgres.credentials]
#    database = "ecoshop_dw"
#    username = "ecoshop"
#    password = "<WAREHOUSE_PASSWORD du .env>"
#    host = "localhost"
#    port = 5433

# 5. Ingestion des trois sources
uv run python pipelines/run_all.py
```

Lightdash est ensuite accessible sur http://localhost:8080.

## Transformations dbt

Les commandes se lancent depuis `dbt_project/`. L'option `--env-file` de uv charge les
identifiants du `.env`, lus par `profiles.yml` via `env_var()` (aucun secret versionné).

```bash
cd dbt_project

uv run --env-file ../.env dbt deps              # installe les packages (dbt_utils, elementary)
uv run --env-file ../.env dbt debug             # vérifie la connexion
uv run --env-file ../.env dbt source freshness  # contrôle la fraîcheur des sources
uv run --env-file ../.env dbt build             # seeds, modèles, snapshots et tests dans l'ordre du DAG
uv run --env-file ../.env dbt test --select "test_type:unit"   # tests unitaires seuls
uv run --env-file ../.env dbt docs generate     # documentation et lignage
uv run --env-file ../.env dbt docs serve --port 8081
```

| Couche | Schéma | Matérialisation | Rôle |
|---|---|---|---|
| Seeds | `seeds` | table | Référentiels maintenus à la main (statuts de commande) |
| Snapshots | `snapshots` | snapshot (SCD2) | Historique des clients (segment, adresse) |
| Staging | `staging` | view | Nettoyage, typage, renommage : un modèle par table source |
| Intermediate | `intermediate` | view / ephemeral | Jointures, calculs et règles métier réutilisables |
| Marts | `marts` | table | Modèle en étoile exposé à Lightdash |

### Modèle en étoile (schéma `marts`)

| Modèle | Grain | Contenu |
|---|---|---|
| `dim_customers` | 1 client | Segment, commune, indicateurs de cycle de vie (sans donnée personnelle directe) |
| `dim_customers_history` | 1 version de client | Historique SCD2 : segment et commune sur chaque période de validité |
| `dim_products` | 1 produit | Prix TTC et HT, coût, marge unitaire |
| `dim_communes` | 1 commune | Département, région, population, coordonnées GPS |
| `fct_orders` | 1 commande | Montants, marge, segment et commune du client à la date de la commande ; incrémental (merge) et contrat appliqué |
| `fct_order_items` | 1 article | Détail par produit et catégorie |
| `fct_dvf_sales` | 1 vente immobilière | Prix, surface, prix au m² des ventes de référence |

Règles de calcul : les prix catalogue sont TTC ; la marge est calculée sur le HT
(macro `amount_excl_vat`, taux de TVA dans la variable `vat_rate`). Pour DVF, le prix
au m² n'est calculé que sur les ventes simples d'un seul logement, et les valeurs hors
bornes (variables `dvf_min_price_per_m2` et `dvf_max_price_per_m2`) sont signalées.

Les schémas sont nommés par la macro `generate_schema_name` : noms simples en `dev` et
`prod`, préfixés en CI (ex. `ci_pr_12_staging`) pour isoler chaque exécution.

### Historique des clients

Le snapshot `snap_customers` historise les changements de segment et d'adresse. Pour
reconstituer l'historique depuis le début des données en développement, le script
`pipelines/replay_history.py` repart d'un schéma brut vide et rejoue la source mois par
mois (ingestion puis snapshot). Il efface `raw_ecoshop` : il ne doit jamais être lancé
en production, où l'historique s'accumule à chaque exécution quotidienne.

## Qualité des données

| Type de test | Exemples |
|---|---|
| Génériques | `unique`, `not_null`, `accepted_values`, `relationships` |
| Packages | `dbt_utils.expression_is_true`, `accepted_range`, `unique_combination_of_columns` |
| Générique personnalisé | `positive_value` (prix, coûts, quantités, prix au m²) |
| Singuliers | Pas de vente à perte sans remise ; part des commandes à perte sous 10 % ; continuité de l'historique SCD2 |
| Unitaires | Calcul des montants et de la marge ; grain vente et prix au m² DVF |
| Anomalies (Elementary) | Volume de commandes par jour comparé aux 30 jours précédents |

Observabilité : le package Elementary enregistre le résultat de chaque exécution dans le
schéma `elementary`. Les alertes sont publiées en français sur Slack par un script dédié
(le webhook est lu dans `SLACK_WEBHOOK_URL`, variable du `.env`) :

```bash
uv run python scripts/slack_alerts.py --apercu   # affiche le message sans l'envoyer
uv run python scripts/slack_alerts.py            # envoie une alerte en cas d'anomalie

cd dbt_project
uv run --env-file ../.env edr report --project-dir . --profiles-dir .   # rapport HTML
```

## Orchestration (Airflow + Cosmos)

Airflow tourne en local dans un profil Docker Compose dédié, lancé uniquement à la
demande. Sa configuration reproduit celle de production : Airflow 3.3.2, mode
`standalone`, LocalExecutor et métadonnées dans PostgreSQL.

```bash
docker compose --profile airflow up -d --build   # interface : http://localhost:8082
docker compose --profile airflow stop            # arrêt (libère la mémoire)
```

Le DAG `ecoshop_quotidien` s'exécute chaque nuit à 2 h (UTC) :

```
ingestion_dlt -> fraicheur_sources -> transformations_dbt (Cosmos) -> alertes_qualite_slack
```

| Tâche | Rôle |
|---|---|
| `ingestion_dlt` | Chargement des trois sources (`pipelines/run_all.py`), deux nouvelles tentatives en cas d'échec |
| `fraicheur_sources` | `dbt source freshness` ; envoie aussi, une fois par run, les métadonnées du projet à Elementary |
| `transformations_dbt` | Projet dbt rendu par Cosmos : une tâche par seed, modèle et snapshot, suivie de ses tests ; les tests portant sur plusieurs modèles sont des tâches à part |
| `alertes_qualite_slack` | Synthèse qualité du run en français, exécutée même si une étape a échoué |

Toute tâche en échec publie également une alerte Slack en français. L'image Airflow
contient deux environnements Python séparés : celui d'Airflow (avec Cosmos) et
`/opt/ecoshop-venv`, construit depuis `uv.lock`, où dbt et dlt s'exécutent en
sous-processus, sans conflit de dépendances.

## Notebooks

| Notebook | Contenu |
|---|---|
| `notebooks/01_apercu_sources.ipynb` | Aperçu du simulateur et d'un fichier DVF avec les fonctions des pipelines |
| `notebooks/02_controle_marts.ipynb` | Indicateurs, CA mensuel et prix au m² à partir des marts |

Le code exécuté en production reste dans les fichiers `.py` ; les notebooks
importent ces fichiers ou interrogent l'entrepôt.

## Qualité du code

Le code Python suit PEP 8 (lignes de 79 caractères), vérifié avec ruff :

```bash
uv run ruff check .
uv run ruff format --check .
```

## Structure du dépôt

```
├── docker-compose.yml        # Stack locale (PostgreSQL, Lightdash, S3) et profil airflow
├── airflow/
│   ├── Dockerfile            # Airflow 3.3.2 + Cosmos, environnement dbt/dlt isolé
│   └── dags/
│       └── ecoshop_daily.py  # DAG quotidien ecoshop_quotidien
├── .dlt/config.toml          # Configuration dlt (non sensible)
├── pipelines/
│   ├── fake_data.py          # Simulateur du back-office e-commerce
│   ├── ecoshop_pipeline.py   # Source 1 : e-commerce -> raw_ecoshop
│   ├── geo_pipeline.py       # Source 2 : API Géo -> raw_geo
│   ├── dvf_pipeline.py       # Source 3 : DVF -> raw_dvf
│   ├── run_all.py            # Point d'entrée unique de l'ingestion
│   └── replay_history.py     # Rejeu de l'historique (développement uniquement)
├── scripts/
│   └── slack_alerts.py       # Alertes qualité en français sur Slack
├── notebooks/                # Exploration et contrôles (Jupyter)
└── dbt_project/
    ├── dbt_project.yml       # Couches, schémas, matérialisations et variables
    ├── profiles.yml          # Connexions dev / ci / prod / elementary (variables d'environnement)
    ├── packages.yml          # dbt_utils, elementary (versions figées dans package-lock.yml)
    ├── macros/               # generate_schema_name, macros financières, surcharge snapshot
    ├── seeds/                # order_status_mapping.csv
    ├── snapshots/            # snap_customers (SCD2)
    ├── tests/                # tests singuliers et test générique positive_value
    └── models/
        ├── staging/          # ecoshop/, geo/, dvf/ : sources, modèles et tests
        ├── intermediate/     # valorisation, géolocalisation, ventes DVF, tests unitaires
        └── marts/            # dimensions et faits exposés à Lightdash
```

## Avancement

- [x] Étape 0 : initialisation du dépôt
- [x] Étape 1 : stack Docker locale
- [x] Étape 2 : ingestion dlt (3 sources)
- [x] Étape 3 : fondations dbt (sources, fraîcheur, staging, seed, tests)
- [x] Étape 4 : modélisation métier (packages, macros, intermediate, marts en étoile, contrat)
- [x] Étape 5 : dbt avancé (snapshot SCD2, incrémental, tests singuliers et unitaires, Elementary, alertes Slack)
- [x] Étape 6 : orchestration Airflow + Cosmos (DAG quotidien, alertes Slack en français)
- [ ] Étape 7 : couche sémantique et dashboards Lightdash
- [ ] Étape 8 : CI/CD GitHub Actions
- [ ] Étape 9 : déploiement sur VPS
