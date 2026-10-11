-- Anonymised: customer_key is the dense order of first purchase (ties by source id). The source Customer ID is not carried.
with k as (
    select source_customer_id, min(invoice_ts) first_ts, max(invoice_ts) last_ts, count(distinct invoice_no) n_invoices_all
    from {{ ref('stg_lines') }} where exclusion_reason is null and source_customer_id is not null group by 1
),
cty as (
    select source_customer_id, mode(country) as country
    from {{ ref('stg_lines') }} where exclusion_reason is null and source_customer_id is not null group by 1
)
select row_number() over (order by first_ts, source_customer_id) as customer_key,
       source_customer_id as _src_id, first_ts, last_ts, n_invoices_all, cty.country
from k join cty using (source_customer_id)
