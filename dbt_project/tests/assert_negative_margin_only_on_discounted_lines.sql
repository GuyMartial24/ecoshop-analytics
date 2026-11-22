-- Règle métier : une ligne vendue à perte doit forcément porter une remise.
--
-- Une marge négative est acceptable sur une ligne remisée (opération commerciale),
-- mais sans remise elle trahit une erreur de prix catalogue ou de coût d'achat.
-- Un test singulier échoue s'il renvoie au moins une ligne.

select
    order_item_id,
    order_id,
    product_id,
    unit_price,
    discount_rate,
    net_amount_excl_vat,
    cost_amount,
    margin_amount

from {{ ref('fct_order_items') }}
where is_revenue
  and margin_amount < 0
  and coalesce(discount_rate, 0) = 0
