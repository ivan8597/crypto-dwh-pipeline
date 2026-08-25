.PHONY: up down extract load-dwh dbt-build dbt-docs sync-ch run-all ci-check

up:
	docker compose up -d --build

down:
	docker compose down

extract:
	docker compose exec airflow-scheduler python /opt/airflow/src/extract.py

load-dwh:
	docker compose exec airflow-scheduler python /opt/airflow/src/load_to_dwh.py

dbt-build:
	docker compose run --rm dbt bash -c "dbt deps --profiles-dir . && dbt build --profiles-dir . --target dev"

dbt-docs:
	docker compose run --rm -p 8081:8080 dbt bash -c "dbt deps --profiles-dir . && dbt docs generate --profiles-dir . && dbt docs serve --profiles-dir . --host 0.0.0.0 --port 8080"

sync-ch:
	docker compose exec airflow-scheduler python /opt/airflow/src/sync_to_ch.py

run-all: up extract load-dwh dbt-build sync-ch

ci-check:
	docker compose config -q
	pip install -q -r requirements-dev.txt
	ruff check src/ dags/
	pytest tests/ -v
