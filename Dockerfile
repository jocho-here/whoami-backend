FROM python:3.9.4-slim

ENV POETRY_VERSION=1.1.5 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    VENV_PATH="/app/.venv"

ENV PATH="$VENV_PATH/bin:$PATH"

RUN apt-get -yq update && \
    apt-get install -yq build-essential libpq-dev postgresql

RUN pip install --no-cache poetry
RUN pip install -U poetry

WORKDIR /app
COPY poetry.lock pyproject.toml alembic.ini ./
COPY whoami_back ./whoami_back
COPY alembic ./alembic

RUN poetry install

ENTRYPOINT ["/bin/bash", "-c"]
