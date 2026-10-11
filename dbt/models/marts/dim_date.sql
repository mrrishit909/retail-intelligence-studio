with b as (select min(cast(invoice_ts as date)) lo, max(cast(invoice_ts as date)) hi from {{ ref('stg_lines') }}),
d as (select cast(unnest(generate_series(lo, hi, interval 1 day)) as date) as dt from b)
select
    cast(strftime(dt, '%Y%m%d') as integer) as date_key,
    dt as date,
    cast(date_trunc('week', dt) as date) as week_start,
    strftime(dt, '%Y-%m') as month,
    isodow(dt) as iso_weekday,
    dayname(dt) as weekday_name,
    -- complete Monday weeks: the week has data coverage from Monday to Sunday inside the observed window
    (cast(date_trunc('week', dt) as date) >= (select cast(date_trunc('week', lo + 6) as date) from b)
     and cast(date_trunc('week', dt) as date) + 6 <= (select hi - 3 from b)) as in_complete_week
from d
