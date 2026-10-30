#!/bin/sh
set -eu

if [ "${1:-web}" = "web" ]; then
  python manage.py migrate --noinput
  python manage.py bootstrap_groups
  exec python manage.py runserver 0.0.0.0:8000
fi

if [ "$1" = "worker" ]; then
  i=0
  until python manage.py migrate --check >/dev/null 2>&1; do
    i=$((i + 1))
    if [ "$i" -gt 60 ]; then
      echo "database migrations were not applied in time" >&2
      exit 1
    fi
    sleep 1
  done
  exec celery -A config worker -l info
fi

exec "$@"
