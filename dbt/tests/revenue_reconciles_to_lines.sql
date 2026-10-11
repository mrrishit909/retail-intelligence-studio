-- Fails (returns a row) if fact_lines amount differs from raw amount minus excluded amount.
with raw as (select sum(round(quantity * price, 4)) a from {{ ref('stg_raw') }}),
exc as (select coalesce(sum(amount), 0) a from {{ ref('stg_lines') }} where exclusion_reason is not null),
kept as (select sum(amount) a from {{ ref('fact_lines') }})
select raw.a, exc.a, kept.a from raw, exc, kept where abs(raw.a - exc.a - kept.a) > 0.01
