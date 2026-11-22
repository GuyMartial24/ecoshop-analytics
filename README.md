#  EcoShop Analytics
> Plateforme analytique e-commerce & immobilière (DVF) — dlt · dbt · PostgreSQL · Lightdash

## 🎯 Objectif

Projet d'Analytics Engineering de bout en bout : ingestion de trois sources (un back-office
e-commerce simulé, le référentiel géographique officiel et les transactions immobilières
réelles DVF), transformation avec dbt et restitution dans des dashboards Lightdash.

## 🏗️ Architecture

```
[Back-office simulé]   [API Géo]            [DVF data.gouv.fr]
   (Faker)          (geo.api.gouv.fr)      (CSV géolocalisés)
        └──────────────── dlt ─────────────────┘
                           ▼
┌──────────────── PostgreSQL (Docker) ────────────────┐
│ raw_ecoshop · raw_geo · raw_dvf   (Bronze, dlt)     │
│ staging · intermediate · marts    (dbt, à venir)    │
└──────────────────────────┬──────────────────────────┘
                           ▼
                Lightdash (Docker) → dashboards
```

## 🧰 Stack technique

| Rôle | Outil |
|---|---|
| Ingestion | dlt (data load tool) |
| Entrepôt | PostgreSQL 16 |
| Transformation | dbt (à venir) |
| BI | Lightdash (+ stockage S3 SeaweedFS en local) |
| Orchestration | Airflow + Cosmos (à venir) |
| Infra | Docker Compose, GitHub Actions, VPS |

## 📥 Sources de données

| Source | Type | Schéma | Stratégie de chargement |
|---|---|---|---|
| Back-office EcoShop | Simulée (Faker, déterministe et évolutive) | `raw_ecoshop` | `merge` incrémental sur `updated_at` (clients, commandes), `replace` (produits) |
| [API Géo](https://geo.api.gouv.fr) | API REST publique | `raw_geo` | `replace` (référentiel complet) |
| [DVF géolocalisées](https://files.data.gouv.fr/geo-dvf/) | Fichiers CSV Open Data | `raw_dvf` | Incrémental par fichier (`Last-Modified`) + remplacement par partition (`delete-insert`) |

Les années et départements DVF se règlent dans `.dlt/config.toml` (section `[sources.dvf]`).

## 🚀 Démarrage rapide

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

## 📁 Structure du dépôt

```
├── docker-compose.yml        # Stack locale (PostgreSQL, Lightdash, S3)
├── .dlt/config.toml          # Configuration dlt (non sensible)
└── pipelines/
    ├── fake_data.py          # Simulateur du back-office e-commerce
    ├── ecoshop_pipeline.py   # Source 1 : e-commerce -> raw_ecoshop
    ├── geo_pipeline.py       # Source 2 : API Géo -> raw_geo
    ├── dvf_pipeline.py       # Source 3 : DVF -> raw_dvf
    └── run_all.py            # Point d'entrée unique de l'ingestion
```

## 🗺️ Avancement

- [x] Étape 0 : initialisation du dépôt
- [x] Étape 1 : stack Docker locale
- [x] Étape 2 : ingestion dlt (3 sources)
- [ ] Étapes 3 à 5 : modélisation dbt (staging, intermédiaire, marts, snapshots, tests)
- [ ] Étape 6 : orchestration Airflow + Cosmos
- [ ] Étape 7 : couche sémantique et dashboards Lightdash
- [ ] Étape 8 : CI/CD GitHub Actions
- [ ] Étape 9 : déploiement sur VPS
