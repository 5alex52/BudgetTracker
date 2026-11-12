#!/bin/sh
# Backend container entrypoint: applies migrations, then runs the given command.
set -e

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    echo "[entrypoint] applying database migrations (alembic upgrade head)"
    alembic upgrade head
fi

exec "$@"
