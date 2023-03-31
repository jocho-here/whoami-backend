# whoami backend



## Technologies
| | |
|:-- |:-- |
|**Language**|Python 3.9|
|**API Server Framework**|[FastAPI](https://fastapi.tiangolo.com/) + [uvicorn](https://www.uvicorn.org/)|
|**Database**|[Postgre SQL](https://www.postgresql.org/)|
|**DB Toolkit**|[SQLAlchemy Core](https://github.com/sqlalchemy/sqlalchemy) + [asyncpg](https://github.com/MagicStack/asyncpg) + [psycopg2](https://github.com/psycopg/psycopg2/)|
|**Deployment**|[Heroku](https://www.heroku.com/)|
|**Package Manager**|[Poetry](https://python-poetry.org/)|
|**SMTP**|[Sendgrid](https://sendgrid.com/)|



## Architecture
### Deployment (Heroku)
- Heroku + Docker for the API
- Heroku + Postgres for the DB
- With [heroku.yml](./heroku.yml), we are specifying Dyno to build a Docker image using the [Dockerfile](./Dockerfile)

### Local (Docker Compose)
- We use [docker-compose.yml](./docker-compose.yml) to orchestrate the local development.
- [docker-compose.override.yml](./docker-compose.override.yml) is used to overwrite settings



## Setting up the local devlopment environment
### Running DB and API server on Docker containers
Use Makefile commands
1. Create database `make db`
2. Then, run Alembic DB migration `make alembic`
3. Finally, start the API server `make api`
4. When you want to clean them up `make clean`

### Preparing to develop whoami API server
1. `cp sample.env .env` and edit `DB_USER` and `DB_PASSWORD` to the correct ones
- Docker Compose file loads environment variables from `.env`
2. `poetry install` to prepare Python virtual environment



## Useful Commands [Heroku]
### Running command on the Dyno
- `heroku run "command"`
- For example, if you want to run alembic
    - `heroku run "alembic upgrade head"`

### Adding heroku environment variables
- `heroku config:set <key>=<value>`

### Look at the logs
- `heroku logs --tail`



## Useful Commands [Local]
### Build the backend Docker image
`make build`

### Git push to both GitHub and Heroku
`make push`

### Clean up the Docker everything
`make clean`

### Installing dependencies
- `make install`

### Linting
- `make lint`

### Running the DB
- `make db` or `docker compose up -d database`

### Running the API server
- `make api` - Running the API server in a Docker container
- `make api-local` - Running the API server NOT in a Docker container

### Alembic Commands
- `make alembic-local` - Running the alembic changes from the local host Poetry
- `make alembic` - Running the alembic changes in a Docker container
- `poetry run alembic current`
- `poetry run alembic upgrade head`
- `poetry run alembic revision -m "create a new table"`
