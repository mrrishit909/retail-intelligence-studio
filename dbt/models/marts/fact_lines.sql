select
    s.raw_id, s.invoice_no, p.product_key, c.customer_key, dd.date_key, ct.country_key,
    s.sku, s.invoice_ts, dd.week_start, dd.month, s.quantity, s.unit_price, s.amount,
    s.line_class, s.nonproduct_class, s.is_guest, s.sheet
from {{ ref('stg_lines') }} s
join {{ ref('dim_product') }} p using (sku)
left join {{ ref('dim_customer') }} c on c._src_id = s.source_customer_id
join {{ ref('dim_date') }} dd on dd.date = cast(s.invoice_ts as date)
join {{ ref('dim_country') }} ct on ct.country = s.country
where s.exclusion_reason is null
