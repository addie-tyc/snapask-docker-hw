#!/usr/bin/env bash

airflow db init
airflow db init

airflow users create \
    -e addiechung.tyc@gmail.com \
    -f addie \
    -l chung \
    -u admin \
    -p password \
    -r Admin

airflow connections add 'RDS-snapask' \
    --conn-type 'mysql' \
    --conn-login 'USER' \
    --conn-password 'PASSWORD' \
    --conn-host 'HOST' \
    --conn-port '3306' \
    --conn-schema 'snapask'

exec airflow webserver -p 8080 & exec airflow scheduler