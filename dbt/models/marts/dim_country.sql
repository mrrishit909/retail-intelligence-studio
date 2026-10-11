select row_number() over (order by country) as country_key, country
from (select distinct country from {{ ref('stg_lines') }} where exclusion_reason is null)
