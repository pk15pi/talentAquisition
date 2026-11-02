"""Gunicorn process settings for the production container.

The development Compose command is ``web-dev`` and still uses runserver.
Production Compose runs ``web``, which execs Gunicorn with this file.
"""

import os

bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:8000")
workers = int(os.environ.get("GUNICORN_WORKERS", "3"))
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "120"))
graceful_timeout = 30
keepalive = 5
accesslog = "-"
errorlog = "-"
capture_output = True
# Gunicorn is not published on the host in production. Nginx is the edge.
forwarded_allow_ips = os.environ.get("GUNICORN_FORWARDED_ALLOW_IPS", "*")
