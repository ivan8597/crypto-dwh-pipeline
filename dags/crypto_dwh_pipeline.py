import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

sys.path.insert(0, "/opt/airflow/src")
from extract import run as extract_run
from load_to_dwh import load_keys
from sync_to_ch import sync as sync_ch_run


def _extract(**context):
    return extract_run()


def _load_dwh(**context):
    return load_keys(context["ti"].xcom_pull(task_ids="extract") or [])


def _sync_ch(**context):
    return sync_ch_run()


with DAG(
    dag_id="crypto_dwh_pipeline",
    description="API -> S3 -> GreenPlum(PG) -> DBT -> ClickHouse",
    schedule="@hourly",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "data-engineer",
        "retries": 3,
        "retry_delay": timedelta(minutes=2),
        "retry_exponential_backoff": True,
    },
    tags=["pet", "crypto", "dwh"],
) as dag:
    t_extract = PythonOperator(task_id="extract", python_callable=_extract)
    t_load_dwh = PythonOperator(task_id="load_to_dwh", python_callable=_load_dwh)
    t_dbt = BashOperator(
        task_id="dbt_build",
        bash_command=(
            "cd /opt/airflow/dbt && dbt deps --profiles-dir . && "
            "dbt build --profiles-dir . --target dev"
        ),
    )
    t_sync_ch = PythonOperator(task_id="sync_to_clickhouse", python_callable=_sync_ch)
    t_extract >> t_load_dwh >> t_dbt >> t_sync_ch
