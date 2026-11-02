#!/bin/sh
set -eu

wait_for_migrations() {
  i=0
  until python manage.py migrate --check >/dev/null 2>&1; do
    i=$((i + 1))
    if [ "$i" -gt 60 ]; then
      echo "database migrations were not applied in time" >&2
      exit 1
    fi
    sleep 1
  done
}

case "${1:-web}" in
  web)
    python manage.py migrate --noinput
    python manage.py bootstrap_groups
    python manage.py collectstatic --noinput
    # Nginx runs as a different user and only mounts this tree, not /app/media.
    chmod -R a+rX /app/staticfiles
    exec gunicorn config.wsgi:application --config gunicorn.conf.py
    ;;
  web-dev)
    python manage.py migrate --noinput
    python manage.py bootstrap_groups
    exec python manage.py runserver 0.0.0.0:8000
    ;;
  worker)
    wait_for_migrations
    exec celery -A config worker -l info
    ;;
  *)
    exec "$@"
    ;;
esac
