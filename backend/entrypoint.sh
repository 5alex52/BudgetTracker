#!/bin/sh
# Точка входа backend-контейнера: применяет миграции и запускает переданную команду.
set -e

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    echo "[entrypoint] applying database migrations (alembic upgrade head)"
    alembic upgrade head
fi

exec "$@"
