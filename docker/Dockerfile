# syntax=docker/dockerfile:1

##### VIRTUAL ENVIRONMENT BASE. ####
FROM python:3.13-slim-bookworm AS venv-base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_VERSION=2.3.1 \
    APP_WORKDIR=/opt/app

RUN pip install poetry==$POETRY_VERSION

#### REQUIREMENTS BUILD. ####
FROM venv-base AS stock-trader-build

WORKDIR $APP_WORKDIR

# Copy over the project's poetry config files
COPY pyproject.toml pyproject.toml
COPY poetry.lock poetry.lock

# Only install main dependencies
RUN poetry install --only main --no-interaction --no-ansi --no-root

#### TEST BUILD. ####
FROM stock-trader-build AS stock-trader-test-build

# Only install the test dependencies
RUN poetry install --only test --no-root

#### INTERMEDIATE BUILD. ####
# FROM ${PROD_BUILD_REQ_NAME} AS stock-trader-base-build

#### PRODUCTION IMAGE. ####
FROM python:3.13-slim-bookworm AS stock-trader-prod

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_VIRTUAL_ENV=/opt/app/.venv

ENV PATH="$APP_VIRTUAL_ENV/bin:$PATH"

RUN addgroup --system app &&\
    adduser --system --group app &&\
    mkdir /app &&\
    chown app:app /app

WORKDIR /app

COPY --chown=app:app --from=stock-trader-build $APP_VIRTUAL_ENV $APP_VIRTUAL_ENV
COPY --chown=app:app src/stock_trader/ ./stock_trader
COPY --chown=app:app assets/ ./assets

USER app

#### TESTING IMAGE. ####
FROM stock-trader-prod AS stock-trader-tests
COPY --chown=app:app cov.ini cov.ini
COPY --chown=app:app mypy.ini mypy.ini
COPY --chown=app:app pyproject.toml pyproject.toml
COPY --chown=app:app .ruff.toml .ruff.toml
COPY --chown=app:app tests/ ./tests/
