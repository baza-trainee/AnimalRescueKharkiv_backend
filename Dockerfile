FROM python:3.12.5-slim-bullseye

ARG YOUR_ENV

ENV APP=/app
ENV PYTHONFAULTHANDLER=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONHASHSEED=random
ENV PIP_NO_CACHE_DIR=off
ENV PIP_DISABLE_PIP_VERSION_CHECK=on
ENV PIP_DEFAULT_TIMEOUT=100
# Poetry's configuration:
ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_CREATE=false
ENV POETRY_CACHE_DIR='/var/cache/pypoetry'
ENV POETRY_HOME='/opt/poetry'
ENV POETRY_VERSION=1.7.1

ENV PATH="$POETRY_HOME/bin:$PATH"

# System deps:
RUN pip install poetry
RUN apt update && apt install -y libpq-dev gcc && apt install -y curl jq

# Copy only requirements to cache them in docker layer
COPY poetry.lock pyproject.toml $APP/
WORKDIR $APP

#RUN bash -c "source $POETRY_HOME/.poetry/env"

# Project initialization:
RUN poetry install --no-interaction --no-ansi

# Creating folders, and files for a project:
COPY ./app $APP
COPY ./static /static/
COPY ./templates /templates/
