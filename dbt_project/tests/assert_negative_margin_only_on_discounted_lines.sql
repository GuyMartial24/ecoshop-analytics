-- Une ligne vendue à perte doit avoir une remise.

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
