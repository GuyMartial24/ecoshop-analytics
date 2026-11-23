# EcoShop Analytics

Plateforme analytique de bout en bout : ingestion, modélisation, orchestration,
restitution et déploiement continu.
**dlt · PostgreSQL · dbt · Airflow · Lightdash · GitHub Actions**

## Démo en ligne

**https://ecoshop-analytics.duckdns.org** (lecture seule)

| Identifiant | Mot de passe |
|---|---|
| `demo@ecoshop-analytics.duckdns.org` | `EcoShopDemo2026` |

Ouvrir le dashboard **EcoShop Analytics**. Les données sont mises à jour chaque nuit.

![Vue exécutive](docs/images/lightdash-vue-executive.png)

## Contexte et objectif

EcoShop est une boutique en ligne française fictive. Sa direction veut suivre son
activité (chiffre d'affaires, marge, clients) et la mettre en regard du marché
immobilier des villes où vivent ses clients.

L'objectif du projet est de construire une chaîne de données complète et automatisée :

- **ingérer** trois sources hétérogènes (back-office, API, fichiers Open Data) ;
- **modéliser** les données en couches (Bronze, Silver, Gold) jusqu'à un modèle
  dimensionnel testé et historisé ;
- **orchestrer** le traitement chaque nuit et **alerter** en cas d'anomalie ;
- **restituer** les indicateurs dans un dashboard accessible en ligne ;
- **déployer** automatiquement chaque évolution validée.

## Jeux de données

| Source | Nature | Contenu | Volume |
|---|---|---|---|
| Back-office EcoShop | Simulée | Clients, produits, commandes et lignes de commande depuis janvier 2025 | 500 clients, 80 produits, environ 21 000 commandes |
| [API Géo](https://geo.api.gouv.fr) | Réelle, API publique | Communes, départements et régions de France, avec population et coordonnées GPS | 35 000 communes |
| [DVF géolocalisées](https://files.data.gouv.fr/geo-dvf/) | Réelle, Open Data | Ventes immobilières 2024-2025 de Paris, du Rhône et de la Gironde | 515 000 lignes, 200 000 ventes |

Le back-office est produit par un simulateur déterministe qui fait évoluer les données
dans le temps : nouvelles commandes, changements de statut, montée en gamme et
déménagement des clients. Il permet de mettre en œuvre le chargement incrémental et
l'historisation des clients sur des données qui changent réellement.

## Architecture

```mermaid
flowchart LR
    subgraph sources["Sources"]
        A["Back-office EcoShop<br/>(simulé)"]
        B["API Géo"]
        C["DVF"]
    end

    D["dlt<br/>ingestion"]

    subgraph pg["PostgreSQL"]
        E["Bronze<br/>données brutes"]
        F["Silver<br/>staging, intermediate, snapshots"]
        G["Gold<br/>faits et dimensions"]
    end

    H["Lightdash<br/>dashboard"]
    I["Slack<br/>alertes qualité"]
    J["Airflow + Cosmos<br/>DAG quotidien"]

    A --> D
    B --> D
    C --> D
    D --> E
    E -->|dbt| F
    F -->|dbt| G
    G --> H
    G -.->|Elementary| I
    J -.-> D
    J -.-> F
```

| Rôle | Outil |
|---|---|
| Ingestion | dlt |
| Entrepôt | PostgreSQL 16 |
| Transformation et tests | dbt Core 1.12, dbt_utils, Elementary |
| Orchestration | Airflow 3.3 + Astronomer Cosmos |
| Restitution | Lightdash (couche sémantique définie dans dbt) |
| Infrastructure | Docker Compose, GitHub Actions, VPS |

## Modèle de données

Modèle en étoile : deux tables de faits (commandes et ventes immobilières) partagent la
dimension géographique, ce qui permet de croiser le chiffre d'affaires et le prix au m²
d'une même commune.

```mermaid
erDiagram
    fct_orders ||--|{ fct_order_items : "contient"
    dim_customers ||--o{ fct_orders : "passe"
    dim_customers_history ||--o{ fct_orders : "version à la commande"
    dim_products ||--o{ fct_order_items : "concerne"
    dim_communes ||--o{ fct_orders : "commune du client"
    dim_communes ||--o{ fct_dvf_sales : "commune du bien"

    fct_orders {
        varchar order_id PK
        bigint customer_id FK
        text customer_version_id FK
        varchar commune_code FK
        date order_date
        varchar order_status
        numeric net_amount_incl_vat
        numeric margin_amount
    }
    fct_order_items {
        varchar order_item_id PK
        varchar order_id FK
        bigint product_id FK
        int quantity
        numeric net_amount_incl_vat
        numeric margin_amount
    }
    fct_dvf_sales {
        varchar mutation_id PK
        varchar commune_code FK
        date mutation_date
        varchar sale_category
        numeric property_value
        numeric price_per_m2
    }
    dim_customers {
        bigint customer_id PK
        varchar customer_segment
        varchar commune_code FK
        numeric lifetime_revenue_incl_vat
    }
    dim_customers_history {
        text customer_version_id PK
        bigint customer_id FK
        varchar customer_segment
        varchar commune_code
        timestamptz valid_from
        timestamptz valid_to
    }
    dim_products {
        bigint product_id PK
        varchar product_category
        numeric list_price_incl_vat
        numeric unit_cost
    }
    dim_communes {
        varchar commune_code PK
        varchar commune_name
        varchar department_name
        float latitude
        float longitude
    }
```

| Couche | Contenu |
|---|---|
| Bronze | Tables chargées par dlt, sans transformation |
| Silver | Nettoyage et typage (staging), règles métier (intermediate), historique des clients (snapshot SCD2) |
| Gold | Faits et dimensions ci-dessus, exposés à Lightdash |

## Points clés

- **Chargement incrémental** : fusion sur clé pour le back-office, remplacement par
  fichier pour DVF (republié chaque semestre), référentiel rechargé en entier.
- **Historisation SCD2** des clients : chaque commande est rattachée au segment et à
  l'adresse du client à la date de l'achat.
- **Table de faits incrémentale** avec contrat de modèle (colonnes et types garantis).
- **Qualité** : plus de 100 tests (génériques, métier, unitaires, détection
  d'anomalie de volume) et contrôle de fraîcheur des sources.
- **Observabilité** : résultats historisés par Elementary, alertes Slack en français.
- **Orchestration** : une tâche Airflow par modèle dbt grâce à Cosmos.
- **CI/CD** : chaque pull request est testée sur une base vide ; chaque merge est
  déployé automatiquement en production.

## Orchestration et alertes

Le DAG `ecoshop_quotidien` s'exécute chaque nuit : ingestion, contrôle de fraîcheur,
transformations dbt (une tâche par modèle, suivie de ses tests), puis synthèse qualité.

![DAG Airflow rendu par Cosmos](docs/images/dag-airflow-cosmos.png)

Toute anomalie est signalée sur Slack :

![Alertes qualité sur Slack](docs/images/alertes-slack.png)

## Déploiement

```mermaid
flowchart LR
    A["Pull request"] --> B{"CI<br/>lint, ingestion,<br/>dbt build"}
    B -->|succès| C["Merge sur main"]
    C --> D["CD<br/>déploiement sur le VPS"]
    D --> E["Lightdash en ligne<br/>(HTTPS)"]
    B -->|échec| S["Alerte Slack"]
    D -->|échec| S
```

En production, chaque service tourne dans un conteneur Docker avec une limite mémoire.
Seul le dashboard est exposé, en HTTPS derrière un reverse proxy ; l'entrepôt et
l'interface Airflow ne sont pas accessibles depuis Internet. Les secrets restent sur le
serveur et dans GitHub, jamais dans le code.

## Aperçu du dashboard

| Onglet | Contenu |
|---|---|
| Vue exécutive | CA, taux de marge, panier moyen, commandes, évolution mensuelle |
| Cartographie France | CA par commune, prix médian au m² par commune et par département |
| Clients et rétention | Segments, commandes par segment, top 10 des clients, fréquence d'achat |
| Qualité et fraîcheur | Derniers chargements, volumes ingérés, tests en anomalie |

![Cartographie France](docs/images/lightdash-cartographie.jpg)

![Clients et rétention](docs/images/lightdash-clients.png)

![Qualité et fraîcheur](docs/images/lightdash-qualite.png)

## Structure du dépôt

```
├── pipelines/          # Ingestion dlt (trois sources) et simulateur du back-office
├── dbt_project/        # Modèles, tests, snapshot, macros et couche sémantique
├── airflow/            # Image Airflow et DAG quotidien
├── lightdash/          # Graphiques et dashboard versionnés en YAML
├── scripts/            # Alertes Slack et déploiement
├── notebooks/          # Exploration et contrôles
└── .github/workflows/  # CI et CD
```

## Auteur

**Martial GADJEU** | Data & AI Engineer
