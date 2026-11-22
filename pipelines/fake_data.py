"""Simulation du back-office d'EcoShop (système source fictif).

Les données sont déterministes (graines fixes) et évoluent avec le temps :
- les clients changent de segment (Standard -> Premium -> VIP) et déménagent ;
- les commandes changent de statut (pending -> shipped -> delivered...).
Cela permet de tester le chargement incrémental (dlt) et l'historisation SCD2 (dbt).
"""

import bisect
import random
from datetime import datetime, timedelta, timezone

from faker import Faker

fake = Faker("fr_FR")

START_DATE = datetime(2025, 1, 1, tzinfo=timezone.utc)
NB_CUSTOMERS = 500
NB_PRODUCTS = 80

# Communes réelles des départements chargés depuis DVF (75, 69, 33)
COMMUNES = [
    ("75011", "Paris"), ("75015", "Paris"), ("75018", "Paris"), ("75020", "Paris"),
    ("69003", "Lyon"), ("69007", "Lyon"), ("69100", "Villeurbanne"), ("69300", "Caluire-et-Cuire"),
    ("33000", "Bordeaux"), ("33400", "Talence"), ("33600", "Pessac"), ("33700", "Mérignac"),
]

CATEGORIES = {
    "Maison": (15, 120),
    "Jardin": (10, 300),
    "Électronique": (30, 900),
    "Mode": (10, 150),
    "Sport": (15, 400),
}


def generate_products():
    """Catalogue produits : stable d'un run à l'autre."""
    rng = random.Random("products")
    fake.seed_instance(42)
    for product_id in range(1, NB_PRODUCTS + 1):
        category = rng.choice(list(CATEGORIES))
        low, high = CATEGORIES[category]
        unit_price = round(rng.uniform(low, high), 2)
        yield {
            "product_id": product_id,
            "product_name": f"{category} {fake.word().capitalize()}",
            "category": category,
            "unit_price": unit_price,
            "unit_cost": round(unit_price * rng.uniform(0.45, 0.80), 2),
        }


def _customer_created_at(rng: random.Random) -> datetime:
    """Date d'inscription d'un client (premiers tirages de son générateur aléatoire)."""
    return START_DATE + timedelta(days=rng.randint(0, 300), seconds=rng.randint(0, 86_399))


def customer_signup_dates() -> list[tuple[datetime, int]]:
    """Dates d'inscription de tous les clients, triées : (date, customer_id)."""
    return sorted(
        (_customer_created_at(random.Random(f"customer-{customer_id}")), customer_id)
        for customer_id in range(1, NB_CUSTOMERS + 1)
    )


def generate_customers(now: datetime):
    """Clients dans leur état à la date `now` (segment et adresse évoluent)."""
    for customer_id in range(1, NB_CUSTOMERS + 1):
        rng = random.Random(f"customer-{customer_id}")
        fake.seed_instance(customer_id)

        created_at = _customer_created_at(rng)
        if created_at > now:
            continue

        postal_code, city = rng.choice(COMMUNES)
        email = fake.email()
        if rng.random() < 0.05:  # défaut de qualité volontaire, à nettoyer en staging
            email = f"  {email.upper()} "

        customer = {
            "customer_id": customer_id,
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": email,
            "segment": "Standard",
            "postal_code": postal_code,
            "city": city,
            "created_at": created_at,
            "updated_at": created_at,
        }

        # Événements de vie du client, datés à l'avance
        events = []
        if rng.random() < 0.40:
            premium_at = created_at + timedelta(days=rng.randint(30, 300))
            events.append((premium_at, {"segment": "Premium"}))
            if rng.random() < 0.35:
                events.append((premium_at + timedelta(days=rng.randint(60, 300)), {"segment": "VIP"}))
        if rng.random() < 0.20:
            new_postal_code, new_city = rng.choice(COMMUNES)
            moved_at = created_at + timedelta(days=rng.randint(60, 600))
            events.append((moved_at, {"postal_code": new_postal_code, "city": new_city}))

        # On applique uniquement les événements déjà survenus à la date `now`
        for event_at, changes in sorted(events, key=lambda e: e[0]):
            if event_at <= now:
                customer.update(changes)
                customer["updated_at"] = event_at

        yield customer


def _order_timeline(rng: random.Random, created_at: datetime):
    """Historique des statuts d'une commande."""
    timeline = [("pending", created_at)]
    draw = rng.random()
    if draw < 0.05:
        timeline.append(("cancelled", created_at + timedelta(hours=rng.randint(1, 24))))
        return timeline
    shipped_at = created_at + timedelta(hours=rng.randint(12, 72))
    delivered_at = shipped_at + timedelta(days=rng.randint(1, 4))
    timeline += [("shipped", shipped_at), ("delivered", delivered_at)]
    if draw > 0.93:
        timeline.append(("returned", delivered_at + timedelta(days=rng.randint(2, 14))))
    return timeline


def generate_orders(updated_since: datetime, now: datetime):
    """Simule l'endpoint GET /orders?updated_since=... d'une API."""
    products = {p["product_id"]: p for p in generate_products()}
    signups = customer_signup_dates()
    signup_dates = [signed_up_at for signed_up_at, _ in signups]
    day = START_DATE
    while day <= now:
        rng = random.Random(f"orders-{day:%Y-%m-%d}")
        for i in range(rng.randint(15, 45)):
            created_at = day + timedelta(seconds=rng.randint(0, 86_399))
            # Seuls les clients déjà inscrits à la date de la commande peuvent commander
            nb_registered = bisect.bisect_right(signup_dates, created_at)
            draw = rng.random()
            customer_id = signups[int(draw * nb_registered)][1] if nb_registered else None
            items = []
            for line_number in range(1, rng.randint(1, 4) + 1):
                product = products[rng.randint(1, NB_PRODUCTS)]
                items.append({
                    "line_number": line_number,
                    "product_id": product["product_id"],
                    "quantity": rng.randint(1, 3),
                    "unit_price": product["unit_price"],
                    "discount_rate": rng.choice([0, 0, 0, 0.05, 0.10, 0.20]),
                })
            timeline = _order_timeline(rng, created_at)

            # Filtres appliqués APRÈS les tirages aléatoires pour rester déterministe
            if created_at > now or customer_id is None:
                continue
            status, updated_at = [(s, t) for s, t in timeline if t <= now][-1]
            if updated_at <= updated_since:
                continue

            yield {
                "order_id": f"{day:%Y%m%d}-{i:03d}",
                "customer_id": customer_id,
                "status": status,
                "currency": "EUR",
                "created_at": created_at,
                "updated_at": updated_at,
                "items": items,  # liste imbriquée -> table enfant orders__items
            }
        day += timedelta(days=1)
