# -*- coding: utf-8 -*-

from datetime import datetime
import textwrap

from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.operators.data_preparation import DownloadUnzipOperator, \
    EmbulkOperator, CopyTableOperator
from airflow.operators.postgres_operator import PostgresOperator
from airflow.operators.dummy_operator import DummyOperator

import helpers
import recipes.basol_recipes as recipes
from config import DATA_DIR, CONN_ID

default_args = helpers.default_args({"start_date": datetime(2019, 6, 11, 5)})


with DAG("prepare_basol",
         default_args=default_args,
         schedule_interval=None) as dag:

    start = DummyOperator(task_id="start")

    download = DownloadUnzipOperator(
        task_id="download",
        url="https://kelrisks.fra1.digitaloceanspaces.com/basol.zip",
        dir_path=DATA_DIR)

    load = EmbulkOperator(
        task_id="load",
        embulk_config="basol.yml.liquid")

    filter_departements = PythonOperator(
        task_id="filter_departements",
        python_callable=recipes.filter_departements)

    parse_cadastre = PythonOperator(
        task_id="parse_cadastre",
        python_callable=recipes.parse_cadastre)

    join_cadastre = PythonOperator(
        task_id="join_cadastre",
        python_callable=recipes.join_cadastre)

    merge_cadastre = PythonOperator(
        task_id="merge_cadastre",
        python_callable=recipes.merge_cadastre)

    geocode = PythonOperator(
        task_id="geocode",
        python_callable=recipes.geocode)

    normalize_precision = PythonOperator(
        task_id="normalize_precision",
        python_callable=recipes.normalize_precision)

    merge_geog = PythonOperator(
        task_id="merge_geog",
        python_callable=recipes.merge_geog)

    intersect = PythonOperator(
        task_id="intersect",
        python_callable=recipes.intersect)

    add_parcels = PythonOperator(
        task_id="add_parcels",
        python_callable=recipes.add_parcels)

    add_communes = PythonOperator(
        task_id="add_communes",
        python_callable=recipes.add_communes)

    add_version = PythonOperator(
        task_id="add_version",
        python_callable=recipes.add_version)

    create_address_id_index = PostgresOperator(
        task_id="create_address_id_index",
        postgres_conn_id=CONN_ID,
        sql=textwrap.dedent("""
            CREATE INDEX basol_adresse_id_idx
            ON etl.basol_with_version (adresse_id)"""))

    stage = CopyTableOperator(
        task_id="stage",
        postgres_conn_id=CONN_ID,
        source="etl.basol_with_version",
        destination="etl.basol")

    check = PythonOperator(
        task_id="check",
        python_callable=recipes.check)

    start >> download >> load >> filter_departements

    filter_departements >> parse_cadastre >> join_cadastre >> merge_cadastre

    filter_departements >> geocode >> normalize_precision \
        >> merge_geog >> intersect

    [merge_cadastre, intersect] >> add_parcels >> add_communes >> add_version

    add_version >> create_address_id_index >> stage >> check
