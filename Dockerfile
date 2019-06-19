FROM python:3-alpine

ENV PYTHONUNBUFFERED 1
ENV ROOT=/usr/src/nicecream-history
ENV PYTHONPATH="$PYTHONPATH:$ROOT"
ARG PIPENV_OPTIONS="--system --deploy"

RUN apk --no-cache add build-base postgresql-dev postgresql-client

COPY Pipfile Pipfile
COPY Pipfile.lock Pipfile.lock
RUN pip install pipenv
RUN pipenv install ${PIPENV_OPTIONS}

COPY api ${ROOT}/api
COPY crawler ${ROOT}/crawler
COPY alembic ${ROOT}/alembic
COPY tests ${ROOT}/tests

WORKDIR ${ROOT}

EXPOSE 8080

CMD ["gunicorn", "api.api:build", "--bind", "0.0.0.0:8080", "--worker-class", "aiohttp.GunicornWebWorker", "--error-logfile=-"]
