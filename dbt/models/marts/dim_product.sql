-- One row per SKU (upper-cased, trimmed). Family is DERIVED by the first matching rule of seeds/product_family_rules.csv.
with d as (
    select sku, description, count(*) n, max(invoice_ts) last_ts
    from {{ ref('stg_lines') }}
    where exclusion_reason is null and description is not null
    group by 1, 2
),
best as (select sku, upper(description) as description from d qualify row_number() over (partition by sku order by n desc, last_ts desc) = 1),
s as (select distinct sku, nonproduct_class from {{ ref('stg_lines') }} where exclusion_reason is null),
m as (
    select b.sku, r.family, r.priority
    from best b join {{ ref('product_family_rules') }} r on regexp_matches(b.description, r.pattern)
    qualify row_number() over (partition by b.sku order by r.priority) = 1
)
select row_number() over (order by s.sku) as product_key, s.sku, b.description,
       s.nonproduct_class is null as is_product,
       case when s.nonproduct_class is not null then 'Non-product'
            else coalesce(m.family, 'Other') end as family
from s left join best b using (sku) left join m using (sku)
