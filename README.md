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

## Error simulation

Configured using global query params (all optional, applied to any endpoint):

```
?transitiveErrors=true/false          // false by default
&errorProb=0.1~1                      // 0 by default (0% chance)
&explicityError=ERROR_KIND_ENUM      // no default
&latencyProb=0.1~1                    // 0 by default
&latencyMs=123                        // 1000 by default
&malformedProb=0.1~1                  // 0 by default
&malformedSeed=123                    // -1 by default, -1 = random
```

### Two kinds of errors

- **Injected errors** ("ours"): deliberately created by the simulation layer.
- **Organic errors** ("not ours"): real API failures (404, 401, 422, DB down, ...).

Both use the SAME common error body. The ONLY discriminator is the
`x-taylor-api-error: ERROR_KIND_ENUM` header: present iff the error was injected
(never present on organic errors). Outside world must treat both the same,
and use the header to know it was a simulated one.

### Error Kinds

```
{
  RATE_LIMIT                  // this error is BEFORE service call
  API_IS_NOT_AVAILABLE        // this error is BEFORE service call
  UKNOWN_ERROR                // this error is AFTER service call
  INTERNAL_ERROR              // this error is AFTER service call
  I_AM_NOT_TAYLOR_ERROR       // this error is AFTER service call
  MALFORMED_RESPONSE          // this error is AFTER service call
}
```

### Status code mapping

| Error kind            | HTTP status             | Extra headers                 |
|-----------------------|-------------------------|-------------------------------|
| RATE_LIMIT            | 429 Too Many Requests   | Retry-After: 5                |
| API_IS_NOT_AVAILABLE  | 503 Service Unavailable | -                             |
| UKNOWN_ERROR          | 500 Internal Server Error | -                           |
| INTERNAL_ERROR        | 500 Internal Server Error | -                           |
| I_AM_NOT_TAYLOR_ERROR | 403 Forbidden           | -                             |
| MALFORMED_RESPONSE    | 200 OK                  | x-taylor-api-error set        |

MALFORMED_RESPONSE keeps 200 but the response body has a random mutation
(field dropped, type changed, value corrupted), so clients can test their
model validation.

### Common error body

Every error (injected AND organic) must return this body:

```json
{
  "kind": "ERROR_KIND_ENUM or ORGANIC_ERROR",
  "message": "human readable",
  "request_id": "uuid",
  "timestamp": "ISO-8601"
}
```

For organic errors FastAPI's default handlers (404/401/422/500) are overridden
by a global exception handler normalizing into this body. `kind` is
`ORGANIC_ERROR` when not a simulated error.

### Semantics

- `explicityError`: pins the error KIND, but does not force an error on its
  own - the `errorProb` roll is still what decides whether the error fires.
- `errorProb`: probability [0,1] that a request errors. When it hits, the kind
  is `explicityError` if set, otherwise picked at random (uniform) among the
  5 error kinds (MALFORMED_RESPONSE only when triggered by `malformedProb`).
- BEFORE service call: the controller is never called, no side effects.
- AFTER service call: the controller runs fully (side effects committed),
  then the error is returned. This is intentional to test client retry and
  idempotency handling.
- `transitiveErrors=true`: enables transitive (propagating) error kinds.
  Purely a per-request gate: it never triggers errors by itself and holds
  no state between requests. Whether an error fires is decided per request
  by the `errorProb` roll.
- Precedence: RATE_LIMIT > API_IS_NOT_AVAILABLE (BEFORE kinds) >
  UKNOWN_ERROR > INTERNAL_ERROR > I_AM_NOT_TAYLOR_ERROR (AFTER kinds).
  Within the same group a kind is picked at random.
- Precedence vs explicit: when both `errorProb` and `explicityError` are set,
  the roll uses `errorProb` and the kind is `explicityError`.

### Error Injection

Latency Injection: `latencyProb` chance of delaying the request by `latencyMs`
milliseconds. Applied BEFORE the controller runs. Latency never turns into
an error by itself, it only delays.

Malformed Response: `malformedProb` chance of mutating a 2xx JSON response.
Mutation kinds: drop a field, change field type, corrupt a field value.
Seedable with `malformedSeed` for reproducible mutations.

When an error is deliberately created, we need a header "x-taylor-api-error: ERROR_ENUM_NAME".

To implement this we will have decorators on each controller method,

### Client Usage

How an outside API/client should handle each injected error kind. The key
signal is the error KIND (in the common body and the `x-taylor-api-error`
header); the HTTP status is secondary.

#### 1. Errors known to happen BEFORE any real service call

`RATE_LIMIT` (429) and `API_IS_NOT_AVAILABLE` (503): nothing was processed,
no side effects, so it is ALWAYS safe to retry.

- Retry with **exponential backoff + jitter** (e.g. base 100ms, x2 each
  attempt, cap ~30s, full jitter), respecting `Retry-After` on 429.
- These are "fail fast, retry later" errors - the server did zero work.

#### 2. Errors that MAY have inserted a state change

`UKNOWN_ERROR`, `INTERNAL_ERROR`, `I_AM_NOT_TAYLOR_ERROR` (403/500) fire
AFTER the service ran, so a POST/PUT may have actually been applied even
though you got an error back.

- **Do NOT blindly retry** - a retry can create duplicates.
- **Idempotency**: make writes idempotent (client-generated idempotency key
  sent via header/body; server dedupes). Then a retry is safe.
- **Check before create/update**: before a POST, GET the resource (or a
  `HEAD`/existence check) to see if your write already landed; before a PUT,
  read the current state and only mutate the diff you intended.
- **Reconcile on uncertainty**: after an ambiguous error, fetch the target
  and compare with your intent (did the rate/album change?), then decide
  to retry, update, or do nothing.
- **Timeout + bounded retries**: only retry a finite number of times with
  backoff, and treat a persistent 5xx as "give up + report" rather than
  hammering.

#### 3. Malformed responses

`MALFORMED_RESPONSE` returns 200 with a corrupted body.

- Validate response schemas on the client and treat a failed parse as a
  retryable/soft error, never crash on unexpected field types.
- Use a lenient decoder (ignore unknown fields, coerce or reject wrong
  types) and fall back gracefully.

#### 4. General

- Use the `x-taylor-api-error` header to distinguish a *simulated* error
  from a *real* one during testing - the handling logic stays the same, the
  header only tells you it was injected.
- Log the `request_id` from every error body to correlate client-side
  failures with server logs.

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


