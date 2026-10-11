select * from (select (select count(*) from {{ ref('stg_raw') }}) r,
  (select count(*) from {{ ref('stg_lines') }} where exclusion_reason is not null) e,
  (select count(*) from {{ ref('fact_lines') }}) k) where r <> e + k
