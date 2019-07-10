FROM python:3-alpine

ENV PYTHONUNBUFFERED 1
ENV ROOT=/usr/src/nicecream-history
ENV PYTHONPATH="$PYTHONPATH:$ROOT"
ARG PIPENV_OPTIONS="--system --deploy"

RUN apk --no-cache add bash build-base postgresql-dev postgresql-client libressl-dev musl-dev libffi-dev

COPY Pipfile Pipfile
COPY Pipfile.lock Pipfile.lock
RUN pip install 'pipenv==2018.11.26' 'awscli==1.16.194'
RUN pipenv install ${PIPENV_OPTIONS}

COPY api ${ROOT}/api
COPY crawler ${ROOT}/crawler
COPY alembic ${ROOT}/alembic
COPY tests ${ROOT}/tests
COPY docker-entrypoint.sh /docker-entrypoint.sh

WORKDIR ${ROOT}

EXPOSE 8080

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["gunicorn", "api.api:build", "--bind", "0.0.0.0:8080", "--worker-class", "aiohttp.GunicornWebWorker"]
