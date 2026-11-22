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
│ seeds · staging                   (Silver, dbt)     │
│ intermediate · marts              (dbt, à venir)    │
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
| Orchestration | Airflow + Cosmos (à venir) |
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

uv run --env-file ../.env dbt debug             # vérifie la connexion
uv run --env-file ../.env dbt source freshness  # contrôle la fraîcheur des sources
uv run --env-file ../.env dbt build             # seeds, modèles et tests dans l'ordre du DAG
uv run --env-file ../.env dbt docs generate     # documentation et lignage
uv run --env-file ../.env dbt docs serve --port 8081
```

| Couche | Schéma | Matérialisation | Rôle |
|---|---|---|---|
| Seeds | `seeds` | table | Référentiels maintenus à la main (statuts de commande) |
| Staging | `staging` | view | Nettoyage, typage, renommage : un modèle par table source |
| Intermediate | `intermediate` | view | Jointures et règles métier (à venir) |
| Marts | `marts` | table | Modèle en étoile exposé à Lightdash (à venir) |

Les schémas sont nommés par la macro `generate_schema_name` : noms simples en `dev` et
`prod`, préfixés en CI (ex. `ci_pr_12_staging`) pour isoler chaque exécution.

## Structure du dépôt

```
├── docker-compose.yml        # Stack locale (PostgreSQL, Lightdash, S3)
├── .dlt/config.toml          # Configuration dlt (non sensible)
├── pipelines/
│   ├── fake_data.py          # Simulateur du back-office e-commerce
│   ├── ecoshop_pipeline.py   # Source 1 : e-commerce -> raw_ecoshop
│   ├── geo_pipeline.py       # Source 2 : API Géo -> raw_geo
│   ├── dvf_pipeline.py       # Source 3 : DVF -> raw_dvf
│   └── run_all.py            # Point d'entrée unique de l'ingestion
└── dbt_project/
    ├── dbt_project.yml       # Couches, schémas et matérialisations
    ├── profiles.yml          # Connexions dev / ci / prod (variables d'environnement)
    ├── macros/               # generate_schema_name
    ├── seeds/                # order_status_mapping.csv
    └── models/
        └── staging/          # ecoshop/, geo/, dvf/ : sources, modèles et tests
```

## Avancement

- [x] Étape 0 : initialisation du dépôt
- [x] Étape 1 : stack Docker locale
- [x] Étape 2 : ingestion dlt (3 sources)
- [x] Étape 3 : fondations dbt (sources, fraîcheur, staging, seed, tests)
- [ ] Étapes 4 et 5 : modélisation dbt (intermédiaire, marts, incrémental, snapshots, tests avancés)
- [ ] Étape 6 : orchestration Airflow + Cosmos
- [ ] Étape 7 : couche sémantique et dashboards Lightdash
- [ ] Étape 8 : CI/CD GitHub Actions
- [ ] Étape 9 : déploiement sur VPS
