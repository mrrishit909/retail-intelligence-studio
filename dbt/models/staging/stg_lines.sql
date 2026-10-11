-- Classifies every raw row; exclusion_reason is null for rows kept in the star schema. raw = kept + excluded by construction.
with n as (
    select
        raw_id, sheet, sheet_row,
        invoice as invoice_no,
        upper(trim(stock_code)) as sku,
        nullif(trim(description), '') as description,
        quantity, invoice_ts, price as unit_price, customer_id as source_customer_id, country,
        round(quantity * price, 4) as amount,
        (sheet = 'Year 2009-2010' and invoice_ts >= timestamp '2010-12-01') as is_overlap
    from {{ ref('stg_raw') }}
),
d as (
    select n.*,
        row_number() over (
            partition by invoice_no, sku, description, quantity, invoice_ts, unit_price, source_customer_id, country
            order by raw_id) as dup_rank
    from n where not is_overlap
),
x as (
    select n.*, coalesce(d.dup_rank, 0) as dup_rank
    from n left join d using (raw_id)
),
c as (
    select *,
        case
            when regexp_matches(sku, '^[0-9]{5}[A-Z]{0,3}$') or regexp_matches(sku, '^DCGS[0-9]{4}[A-Z]?$') then null
            when sku in ('POST', 'DOT') or regexp_matches(sku, '^C[0-9]$') then 'postage'
            when sku in ('M', 'D', 'S', 'B') or sku like 'ADJUST%' then 'manual_adjustment'
            when sku in ('BANK CHARGES', 'AMAZONFEE', 'CRUK') then 'fees'
            when sku like 'GIFT\_%' escape '\' then 'voucher'
            when sku like 'TEST%' then 'test'
            else 'other'
        end as nonproduct_class
    from x
)
select *,
    case when is_overlap then 'overlap_duplicate' when dup_rank > 1 then 'exact_duplicate' end as exclusion_reason,
    case
        when nonproduct_class is not null then 'nonproduct'
        when invoice_no like 'C%' then 'refund'
        when quantity <= 0 or unit_price <= 0 then 'stock_adjustment'
        else 'sale'
    end as line_class,
    source_customer_id is null as is_guest
from c
