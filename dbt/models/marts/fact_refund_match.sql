-- Written after the Python LIFO matcher (pipelines/cleaning/refunds.py) has populated main.refund_matches.
select m.refund_raw_id, m.sale_raw_id, m.matched_qty, m.refund_qty, m.status
from {{ source('pipeline', 'refund_matches') }} m
join {{ ref('fact_lines') }} f on f.raw_id = m.refund_raw_id
