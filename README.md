# Crypto DWH Pipeline

Pet-проект end-to-end **Data Warehouse** пайплайна:

```
Coinbase API → MinIO (S3, append-only) → PostgreSQL/Greenplum (staging)
                                    → dbt (staging / intermediate / marts)
                                    → ClickHouse (BI)
```

Оркестрация — **Apache Airflow**. Локально PostgreSQL 15 стоит как совместимый стенд вместо Greenplum MPP.

---

## Архитектура

```
┌─────────────┐     extract      ┌──────────┐     load_keys      ┌────────────┐
│ Coinbase    │ ───────────────► │  MinIO   │ ─────────────────► │ PostgreSQL │
│ Exchange    │   JSON ticker    │  (S3)    │   exact keys via   │  staging   │
│ API         │                  │ raw layer│   XCom (no rescan) │            │
└─────────────┘                  └──────────┘                    └─────┬──────┘
                                                                       │
                                                              dbt build│
                                                                       ▼
┌─────────────┐     sync 48h     ┌──────────┐                  ┌────────────┐
│ ClickHouse  │ ◄─────────────── │   dbt    │ ◄────────────────│ intermediate│
│ marts.fct_  │  ReplacingMerge  │  models  │                  │   + marts  │
│ hourly_     │  Tree versions   │          │                  └────────────┘
│ prices      │                  └──────────┘
└─────────────┘
```

| Слой | Технология | Назначение |
|------|------------|------------|
| Ingestion | Coinbase REST + `requests` + `tenacity` | Тикеры BTC-USD, ETH-USD |
| Object storage | MinIO (S3-compatible) | Append-only raw JSON |
| DWH | PostgreSQL 15 (локально) / Greenplum (prod) | Staging-таблицы |
| Transform | dbt Core 1.7 | staging → intermediate → marts |
| Serving | ClickHouse 24.8 | Аналитика, BI |
| Orchestration | Airflow 2.9 | Hourly DAG |

---

## Быстрый старт

**Требования:** Docker, Docker Compose, Make.

```bash
git clone https://github.com/ivan8597/crypto-dwh-pipeline.git
cd crypto-dwh-pipeline

cp .env.example .env
# при желании поменяйте пароли в .env

make up          # поднять весь стек (сборка образов)
make extract     # API → S3
make load-dwh    # S3 → PostgreSQL staging
make dbt-build   # dbt deps + build
make sync-ch     # marts → ClickHouse
```

Или одной командой после `make up`:

```bash
make run-all
```

### UI и порты

| Сервис | URL / порт | Доступ |
|--------|------------|--------|
| Airflow | http://localhost:8080 | `admin` / `admin` |
| MinIO Console | http://localhost:9001 | из `.env` (`S3_ACCESS_KEY` / `S3_SECRET_KEY`) |
| MinIO API | http://localhost:9000 | — |
| PostgreSQL | localhost:5432 | `PG_USER` / `PG_PASSWORD` |
| ClickHouse HTTP | http://localhost:8123 | — |
| ClickHouse native | localhost:9002 | — |

Проверка данных в ClickHouse:

```bash
docker compose exec clickhouse clickhouse-client --query \
  "SELECT * FROM marts.fct_hourly_prices FINAL
   ORDER BY hour_ts DESC LIMIT 10 FORMAT Pretty"
```

Остановка:

```bash
make down
```

---

## Структура репозитория

```
crypto-dwh-pipeline/
├── dags/
│   └── crypto_dwh_pipeline.py   # hourly DAG: extract → load → dbt → sync
├── src/
│   ├── config.py                # env-конфиг
│   ├── s3_client.py             # boto3 → MinIO
│   ├── extract.py               # Coinbase → S3 (возвращает keys)
│   ├── load_to_dwh.py           # S3 keys → staging.crypto_prices_raw
│   └── sync_to_ch.py            # marts → ClickHouse (окно 48 ч)
├── dbt/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── packages.yml             # dbt_utils
│   ├── models/
│   │   ├── staging/             # sources + stg_crypto_prices
│   │   ├── intermediate/        # int_price_metrics
│   │   └── marts/               # fct_hourly_prices + schema tests
│   └── tests/
│       └── assert_no_price_spikes.sql
├── sql/
│   └── init_ch.sql              # CREATE DATABASE/TABLE marts
├── tests/                       # unit-тесты extract / load / transform
├── .github/workflows/ci.yml
├── docker-compose.yml
├── Dockerfile.airflow
├── Dockerfile.dbt
├── Makefile
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml               # ruff + pytest
└── .env.example
```

---

## DAG (Airflow)

`dags/crypto_dwh_pipeline.py` — schedule `@hourly`:

1. **extract** — `PythonOperator` → `extract.run()` → XCom со списком S3 keys  
2. **load_to_dwh** — читает ровно эти keys (без повторного list/scan дня)  
3. **dbt_build** — `BashOperator`: `dbt deps && dbt build`  
4. **sync_to_clickhouse** — окно последних 48 часов в `marts.fct_hourly_prices`

```
extract >> load_to_dwh >> dbt_build >> sync_to_clickhouse
```

Retries: 3, exponential backoff.

---

## dbt-модели

| Модель | Слой | Материализация | Суть |
|--------|------|----------------|------|
| `stg_crypto_prices` | staging | view | дедуп по `(symbol, fetched_at)`, `hour_ts` |
| `int_price_metrics` | intermediate | view | avg/min/max/volatility + lag |
| `fct_hourly_prices` | marts | table | `%` изменения цены час к часу |

Тесты:
- `not_null` на ключевых колонках  
- `unique_combination_of_columns` на `(symbol, hour_ts)`  
- custom: `assert_no_price_spikes` (`|price_change_pct| > 50`)

Документация dbt:

```bash
make dbt-docs
# http://localhost:8081
```

---

## Ключевые решения

1. **Append-only raw** — в S3 пишем только новые объекты; дедупликация в dbt (`row_number()`).
2. **Exact keys через XCom** — extract возвращает список keys, load читает только их → нет лишнего list дня.
3. **S3 paginator** — корректная работа с большим числом объектов.
4. **ClickHouse `ReplacingMergeTree(synced_at)`** — идемпотентные вставки версий; окно **48 часов** покрывает late-arriving данные.
5. **`FINAL` только для демо** — в prod лучше `argMax` / materialized view / уникальность на загрузке.
6. **Секреты только в `.env`** — `.env` в `.gitignore`; CI падает, если файл попал в репозиторий.
7. **PostgreSQL как стенд Greenplum** — синтаксис совместим; MPP/сегменты локально не эмулируются.

---

## Makefile

| Цель | Описание |
|------|----------|
| `make up` | `docker compose up -d --build` |
| `make down` | остановить стек |
| `make extract` | API → S3 |
| `make load-dwh` | S3 → staging |
| `make dbt-build` | `dbt deps && dbt build` |
| `make dbt-docs` | docs serve на :8081 |
| `make sync-ch` | marts → ClickHouse |
| `make run-all` | up + полный прогон |
| `make ci-check` | compose config + ruff + pytest |

---

## Разработка и CI

```bash
pip install -r requirements-dev.txt
ruff check src/ dags/
pytest tests/ -v
```

GitHub Actions (`.github/workflows/ci.yml`):
- **lint-test** — Python 3.11, ruff, pytest, проверка отсутствия `.env`
- **compose-validate** — `docker compose config -q` на базе `.env.example`

---

## Стек

| Компонент | Версия |
|-----------|--------|
| Python | 3.11 |
| Apache Airflow | 2.9 |
| dbt Core / dbt-postgres | 1.7.x |
| ClickHouse | 24.8 |
| MinIO | 2024-06-13 |
| PostgreSQL | 15.7 |
| Docker / Compose | — |

---

## Лицензия

Pet-проект для портфолио. Используйте свободно.
