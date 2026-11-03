FROM python:3.13-slim

# - контейнер не должен кэшировать .pyc и буферизовать stdout
# - poetry ставится только для установки зависимостей, в рантайме не нужен
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

WORKDIR /app

# curl нужен для HEALTHCHECK, больше системных пакетов не требуется:
# все зависимости с C-расширениями (asyncpg, psycopg2-binary, pydantic-core, uvloop, httptools, watchfiles)
# поставляются готовыми колёсами для cp313
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Зависимости ставятся отдельным слоем, чтобы не переустанавливаться при изменении кода.
# INSTALL_DEV=true добавляет dev-группу (pytest, black, ...) — нужно для прогона тестов
# внутри контейнера, в production-сборке группа не устанавливается.
ARG INSTALL_DEV=false

COPY pyproject.toml poetry.lock ./
RUN pip install --upgrade pip \
    && pip install "poetry==2.5.1" \
    && poetry install --only main --no-root --no-ansi \
    && if [ "$INSTALL_DEV" = "true" ]; then poetry install --no-root --no-ansi; fi

COPY . .

RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

ENTRYPOINT ["sh", "/app/entrypoint.sh"]
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
