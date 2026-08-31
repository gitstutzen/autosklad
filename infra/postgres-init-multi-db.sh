#!/bin/bash
# Один контейнер Postgres, отдельная база на каждый сервис (database-per-service
# на уровне логической БД, не отдельных инстансов — упрощает dev-окружение,
# при этом сервисы всё равно не видят чужие таблицы, т.к. подключаются каждый
# к своей базе через свою DATABASE_URL).
set -e

IFS=',' read -ra DBS <<< "$POSTGRES_MULTIPLE_DATABASES"
for db in "${DBS[@]}"; do
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE DATABASE "$db";
    GRANT ALL PRIVILEGES ON DATABASE "$db" TO "$POSTGRES_USER";
EOSQL
done
