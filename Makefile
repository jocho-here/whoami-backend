export BASEVERSION := $(shell cat BASEVERSION)
docker_vars := --use-aliases --rm -d -p 8000:8000

.PHONY: db
db:
	docker-compose up -d database

.PHONY: build
build:
	docker build . -t whoami_back:${BASEVERSION}

.PHONY: api
api: build
	docker-compose run ${docker_vars} backend "gunicorn -w 3 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 whoami_back.api.asgi:app"
#	docker compose run ${docker_vars} backend "gunicorn -b 0.0.0.0:8000 -w 1 -k uvicorn.workers.UvicornWorker whoami_back.api.asgi:app"

.PHONY: alembic
alembic: build
	docker-compose run ${docker_vars} alembic "alembic upgrade head"

.PHONY: lint
lint:
	poetry run flake8 .
	poetry run black .
	poetry run isort .

.PHONY: install
install:
	poetry install

.PHONY: api-local
api-local:
	poetry run uvicorn whoami_back.api.asgi:app --host 0.0.0.0 --port 8000 --reload
#	poetry run gunicorn -w 3 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 whoami_back.api.asgi:app

.PHONY: alembic-local
alembic-local:
	poetry run alembic upgrade head

.PHONY: test-local
test-local:
	poetry run pytest tests

.PHONY: clean
clean:
	docker-compose down

.PHONY: push
push:
	git push origin main
	git push heroku main
