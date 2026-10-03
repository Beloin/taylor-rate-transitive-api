# Taylor Music Rating

The idea here is to create a full-blown rating platform and system that has as it's entrypoint a RESTapi and a gRPC API.

The API will be full of regular API calls, regular CRUD, but also will have forged consistency errors and rate limiting.

## Security

Hardcoded login and password using JWT token:

```
POST /login

Users:

username: duda
pass:     dudinha123pass!!

username: belois
pass:     belois123pass!!

username: taylor
pass:     taylor123pass!!

```

## Initial CRUD

Data is in folders:

```
data/
  albums/
    0001/
      index.json
      music_01.json
      music_02.json
    0002/
      index.json
      music_01.json
      music_02.json
```

### Albums

List all albums and rate them

```
GET     /albums
GET     /albums/:id
GET     /albums/:id/rate
POST    /albums/:id/rate
PUT     /albums/:id/rate/:id
DELETE  /albums/:id/rate/:id
```

### Musics

List all musics and rate them, needs to be album localized.
Rules:
  - You cannot choose a different music that is not on that album.

```
GET     /albums/{id}/musics
GET     /albums/{id}/musics/:id
GET     /albums/{id}/musics/:id/rate
POST    /albums/{id}/musics/:id/rate
PUT     /albums/{id}/musics/:id/rate/:id
DELETE  /albums/{id}/musics/:id/rate/:id
```


### Rate

Rate will be a generic resource, it can go to Albums and Musics.

### Configurations

Here we can reset/setup the API

```
POST /setup/reset-rates
POST /setup/randomize-rates
GET  /setup/cert
```

-> reset-rates: Deletes all generated rates by /randomize-rates.
-> randomize-rates: Creates random rates for all albums and musics, body have a seed, if -1 no seed is provided. Other fields: album_rate_count: int -> how many rates per album, default 2, same for music_rate_count.

Randomize should also use `data/randomize_rates` that should contain a lot of json files that should be a generic description for each music and album to allow better testing.

## Implementation

Everything should be docker and docker-compose.
Should have swagger.
Server should be attached to 0.0.0.0
Server should also be both HTTP and HTTPs, we should generate a priv/pub and cert for this Server and expose public cert at `/setup/cert` so we can download and set as our saved crt in another API.

### DB

Check ./db.puml for entities.
Migration: Just insert if not exists all data on `/data`, this will run in all deployments.
Postgres.

### How to run

#### Docker (recommended)

```bash
docker compose up -d --build
```

- API: `http://localhost:8000` and `https://localhost:8443` (self-signed)
- Swagger: `http://localhost:8000/docs`
- Postgres is exposed on host port `5433` (user/pass/db: `taylor`/`taylor`/`taylor`)
- Migrations run automatically on container start, then data on `/data` is seeded (insert-if-not-exists)

#### Local (without Docker)

Requires [uv](https://docs.astral.sh/uv/). Postgres is still provided by Docker (or point `DATABASE_URL` in `.env` to your own instance):

```bash
docker compose up -d db   # start only postgres

cd backend
uv sync                   # creates/updates .venv
cp .env.example .env      # one-time: all runtime config lives here
uv run alembic upgrade head   # one-time: create schema

uv run python -m app      # that's it - API on http://0.0.0.0:8000 + https://0.0.0.0:8443
```

All configuration is read from `backend/.env` (copy from `.env.example`), no inline env vars needed. Available vars: `DATABASE_URL`, `DATA_DIR`, `CERT_DIR`, `CERT_CN`, `JWT_SECRET`, `HTTP_PORT`, `HTTPS_PORT`.

Or use the venv directly (no `uv run`):

```bash
source .venv/bin/activate
python -m app
```

Note: you cannot run the local API and the Docker `api` service at the same time (both bind 8000/8443). Use `docker compose stop api` first, or keep only `db` running.

Available env vars (see `backend/.env.example`): `DATABASE_URL`, `DATA_DIR`, `CERT_DIR`, `CERT_CN`, `JWT_SECRET`, `HTTP_PORT`, `HTTPS_PORT`.


