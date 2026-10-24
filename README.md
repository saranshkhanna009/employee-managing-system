# Employee Tracker

This repository contains the Employee Tracker frontend, FastAPI backend,
PostgreSQL, Redis, and Nginx gateway. Docker Compose is the supported
all-in-one local and self-managed deployment path. A split Render/Vercel
deployment is documented in
[`DEPLOYMENT.md`](DEPLOYMENT.md).

## Prerequisites

- Docker Engine with Docker Compose v2 (`docker compose version`)
- OpenSSL for generating secrets (`openssl version`)
- A public hostname and a TLS-terminating load balancer or reverse proxy for
  production

The backend and frontend images use pinned Python, Node, and Nginx image tags.
The frontend uses the checked-in `frontend/package-lock.json` through `npm ci`.
The local runtime pins are `backend/.python-version` and `frontend/.nvmrc`.

## Configure

Create the local environment file:

```sh
cp .env.example .env
```

Edit `.env` and replace all placeholder values. Generate the required secrets
with:

```sh
openssl rand -hex 24       # DB_PASSWORD
openssl rand -hex 24       # REDIS_PASSWORD
openssl rand -base64 32    # ENCRYPTION_MASTER_KEY
openssl rand -base64 32    # SECRET_KEY
```

Use the generated hex values for the database and Redis passwords so they are
safe inside the Compose connection URLs. The two base64 values must each
decode to 32 bytes.

The checked-in template uses safe local HTTP defaults. For a local HTTP
deployment, the relevant values are:

```dotenv
ENVIRONMENT=development
DEBUG=true
SESSION_COOKIE_NAME=session
SESSION_COOKIE_SECURE=false
SESSION_COOKIE_SAMESITE=lax
CORS_ORIGINS=["http://localhost:8080"]
VITE_API_URL=http://localhost:8080
```

The cookie name is intentionally changed from `__Host-session`: browsers require
cookies with the `__Host-` prefix to be Secure, which would prevent login over
local HTTP. Use the default `__Host-session` name and Secure cookies in a real
HTTPS deployment.

Set these values for the real deployment:

- `VITE_API_URL` to the public application origin, for example
  `https://app.example.com`.
- `CORS_ORIGINS` to a JSON array containing that same origin.
- `FROM_EMAIL` and the SMTP variables when password-reset email is enabled.
- `SESSION_COOKIE_SECURE=true` and `DEBUG=false` in production.

Compose requires the database, Redis, application keys, CORS origin,
environment, public port, TLS termination mode, and `FROM_EMAIL`. It does not
provide insecure fallback passwords or keys.

For non-Docker development, use the pinned runtimes and install dependencies
inside the project environment:

```sh
python3.12 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.txt
source backend/.venv/bin/activate
cd frontend && npm ci && cd ..
```

On Windows, create the environment with `py -3.12 -m venv backend/.venv`, use
`backend/.venv/Scripts/python.exe` in place of the Linux virtual-environment
path, and activate it with `backend/.venv/Scripts/Activate.ps1`. Docker
deployment does not require these local environments.

## TLS termination

The Compose Nginx gateway intentionally listens on HTTP only and does not
mount repository-local certificates. Set `TLS_TERMINATION=external` and put a
managed load balancer or reverse proxy in front of the published
`${HTTP_PORT}`. That edge must:

1. Own and renew the certificate.
2. Redirect HTTP to HTTPS.
3. Forward `Host`, `X-Forwarded-For`, and `X-Forwarded-Proto`.
4. Restrict the Compose host port to the edge proxy or private network.

Do not publish the Compose HTTP port directly to the public Internet. Local
development can use `http://localhost:${HTTP_PORT}`. The gateway exposes only
the frontend and API; PostgreSQL and Redis have no host port mappings and are
attached only to the internal network.

## Validate and build

Run the Compose configuration check after `.env` is populated:

```sh
docker compose config --quiet
docker compose build
```

The frontend API URL is passed as the `VITE_API_URL` Docker build argument;
changing it requires rebuilding the frontend image.

## Run

Start the complete stack:

```sh
docker compose up -d --build
docker compose ps
```

The `migrate` service waits for PostgreSQL to become healthy. The backend is
held until that service exits successfully, and the gateway waits for healthy
backend and frontend services. Check startup logs with:

```sh
docker compose logs -f migrate backend nginx
```

The local health endpoint is:

```sh
curl --fail http://localhost:8080/health
```

If `HTTP_PORT` differs from `8080`, use that value instead.

## Migrations

Migrations run automatically before the backend starts. To run the same
migration job explicitly against an already configured Compose database:

```sh
docker compose run --rm --build migrate
```

Do not use `docker compose down -v` unless the PostgreSQL and Redis volumes
are intentionally being deleted.

## Test and smoke check

The repository includes backend smoke tests and frontend helper tests. Run them
before building images:

```sh
cd backend
python -m pytest -q
cd ../frontend
npm ci
npm run lint
npm test -- --run
npm run build
cd ..
```

After both runtimes are installed, the same test suite can be run from the
repository root with:

```sh
make test
```

The deployment validation command is:

```sh
docker compose config --quiet && docker compose build
```

After starting the stack, the health smoke check is:

```sh
curl --fail http://localhost:8080/health
```

The image healthchecks also verify the backend, frontend, gateway, PostgreSQL,
and authenticated Redis connectivity through `docker compose ps`. A healthy
container only proves that the process is responding; it does not replace an
authenticated application smoke test.

## Deploy

On the deployment host, copy the repository and a separately managed `.env`
file, verify the edge TLS proxy configuration, then run:

```sh
docker compose config --quiet
docker compose up -d --build --remove-orphans
docker compose ps
```

Keep `.env` outside version control and provide secrets through the host's
secret-management process. Rebuild after changing `VITE_API_URL`, and review
the migration logs after every release.

To stop the stack without deleting persistent data:

```sh
docker compose down
```
