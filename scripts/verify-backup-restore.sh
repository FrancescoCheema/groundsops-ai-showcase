#!/usr/bin/env bash
set -euo pipefail

host="${PGHOST:-127.0.0.1}"
port="${PGPORT:-5432}"
user="${PGUSER:-groundsops}"
source_db="${PGDATABASE:-groundsops}"
restore_db="groundsops_restore_verify_${GITHUB_RUN_ID:-$$}"
dump_file="$(mktemp --suffix=.dump)"
cleanup() { dropdb -h "$host" -p "$port" -U "$user" --if-exists "$restore_db" >/dev/null 2>&1 || true; rm -f "$dump_file"; }
trap cleanup EXIT

pg_dump -h "$host" -p "$port" -U "$user" --format=custom --compress=9 --no-owner --file="$dump_file" "$source_db"
pg_restore --list "$dump_file" >/dev/null
createdb -h "$host" -p "$port" -U "$user" "$restore_db"
pg_restore -h "$host" -p "$port" -U "$user" --dbname="$restore_db" --no-owner --no-acl "$dump_file"
table_count="$(psql -h "$host" -p "$port" -U "$user" -d "$restore_db" -Atc "select count(*) from information_schema.tables where table_schema='public';")"
[[ "$table_count" -gt 0 ]] || { echo "Restore verification found no application tables."; exit 1; }
echo "Backup restore verified in isolated database ($table_count public tables)."

