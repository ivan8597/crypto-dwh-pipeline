with source as (
    select * from {{ source('staging', 'crypto_prices_raw') }}
), deduplicated as (
    select *, row_number() over (partition by symbol, fetched_at order by _loaded_at desc) as rn
    from source
)
select symbol, cast(price as double precision) as price,
       cast(volume_24h as double precision) as volume_24h,
       fetched_at, date_trunc('hour', fetched_at) as hour_ts
from deduplicated
where rn = 1 and price > 0
