# Crypto DWH Pipeline

Pet-проект **API -> S3 -> PostgreSQL/Greenplum -> dbt -> ClickHouse**, оркестрируемый Airflow.

## Архитектура

Coinbase API -> Airflow -> MinIO (S3 raw, append-only) -> PostgreSQL/Greenplum staging -> dbt staging/intermediate/marts -> ClickHouse BI.

Локально PostgreSQL 15 используется как совместимый с Greenplum стенд: production deployment targets Greenplum MPP, поэтому распределение данных и segment-level parallelism локально не проверяются.

## Запуск

```bash
cp .env.example .env
make up
make extract
make load-dwh
make dbt-build
make sync-ch
```

Airflow UI: http://localhost:8080 (admin/admin). Результат в ClickHouse:

```bash
docker compose exec clickhouse clickhouse-client --query "SELECT * FROM marts.fct_hourly_prices FINAL ORDER BY hour_ts DESC LIMIT 10 FORMAT Pretty"
```

## Стек

Python 3.11, Airflow 2.9, dbt Core 1.7.x (pinned for reproducible local development), ClickHouse 24.8, MinIO, PostgreSQL 15 и Docker.

## Ключевые решения

Raw layer append-only: дедупликация выполняется в dbt через `row_number()`. Extract передаёт конкретные S3 keys в load через XCom, поэтому повторного скана дня нет. Для S3 используется paginator. ClickHouse ingestion выполняется вставкой новых версий строк, а дедупликация — через `ReplacingMergeTree(synced_at)`.

ClickHouse sync intentionally reprocesses a **rolling 48-hour window** to handle late-arriving and corrected DWH records. `FINAL` используется только для демонстрационной выборки; в production предпочтительнее argMax/view или гарантия уникальности на этапе загрузки.

Секреты передаются только через `.env`; CI проверяет отсутствие `.env` в репозитории.

## Проверки

```bash
pip install -r requirements-dev.txt
ruff check src/ dags/
pytest tests/ -v
```
