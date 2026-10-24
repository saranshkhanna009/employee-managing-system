#!/bin/sh
set -eu

# Compose's migration service supplies an explicit command. Render's free web
# service supplies no command and sets RUN_MIGRATIONS=true, so migrations run
# once before the application process starts.
if [ "$#" -gt 0 ]; then
    exec "$@"
fi

if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
    alembic -c /app/alembic.ini upgrade head
fi

exec gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind "0.0.0.0:${PORT:-8000}" \
    --access-logfile - \
    --error-logfile -
