# Employee Tracker deployment guide

This guide covers the existing Docker Compose deployment and the split
Render/Vercel deployment:

- **Render** runs the backend Docker web service and its Alembic migrations.
- **Vercel** builds and serves the frontend SPA.
- **Docker Compose** remains available for local development and a
  self-managed deployment.

## Render backend

The root [`render.yaml`](render.yaml) describes an Employee Tracker Docker web
service using the `backend` build context and checked-in `backend/Dockerfile`.
The service uses Render's current free web-service plan by default; change the
plan in the Blueprint or dashboard if the workload needs more capacity. Because
Render free web services do not support pre-deploy commands, the container runs
the following Alembic migration before Gunicorn starts and checks `/health`:

```sh
alembic -c /app/alembic.ini upgrade head
```

The Render service uses the `backend` directory as its root. In the Render
dashboard, use the repository root as the Blueprint location. The Docker paths
in `render.yaml` are relative to that service root, so Render uses
`./Dockerfile` with `.` as its build context. The migration runs inside the
built image on each container start and is safe to re-run.

### Provision the data services

The Blueprint creates a Render PostgreSQL 16 database named
`employee-tracker-db` and injects its connection string into `DATABASE_URL`.
The Render `DATABASE_URL` **must be a PostgreSQL URL**. The application uses
SQLAlchemy's asyncpg driver and normalizes Render's standard PostgreSQL URL
schemes automatically. The preferred value is the asyncpg scheme, for example:

```text
postgresql+asyncpg://USER:PASSWORD@HOST/DATABASE
```

If you use an existing Render database instead of the Blueprint database, a
connection URL beginning with `postgres://` or `postgresql://` can be used
directly; the backend converts the scheme at startup. Do not use SQLite, MySQL,
or another database URL.

Redis is included for the Docker Compose deployment. The current Employee
Tracker request path does not use Redis, so a separate Render Redis service is
not required for this deployment. If Redis-backed features are enabled later,
provide `REDIS_URL` through Render's environment-variable manager rather than
adding credentials to `render.yaml` or source control.

### Configure the web service

1. Create a Render Blueprint from this repository and use the root
   `render.yaml`. It creates the PostgreSQL database and web service together.
2. Set the `sync: false` variables shown in `render.yaml` in Render's
   dashboard:
   `ENCRYPTION_MASTER_KEY`, `SECRET_KEY`,
   `CORS_ORIGINS`, `FROM_EMAIL`, `SMTP_HOST`, `SMTP_USER`, and `SMTP_PASS`.
3. Generate `ENCRYPTION_MASTER_KEY` and `SECRET_KEY` as base64-encoded 32-byte
   values. For example, generate each value locally with:

   ```sh
   openssl rand -base64 32
   ```

4. Set `CORS_ORIGINS` to a JSON array containing the deployed frontend origin.
   For example:

   ```text
   ["https://employee-tracker.vercel.app"]
   ```

5. Deploy the service. The container runs the Alembic migration before
   starting Gunicorn and Render uses `/health` for health checks.

Verify the deployed backend with:

```sh
curl --fail https://employee-tracker-api.onrender.com/health
```

Replace the hostname with the actual Render service hostname.

The Blueprint sets `SESSION_COOKIE_SAMESITE=none` and
`SESSION_COOKIE_SECURE=true` because a Vercel frontend and Render backend are
separate origins and the Employee Tracker uses cookie-based authentication.

The Blueprint defaults to Render's free plans for a low-cost preview. Free web
services sleep when idle, cannot send SMTP traffic on port 587, and free
PostgreSQL databases expire after 30 days without backups. Upgrade both plans
before using this deployment for production.

## Vercel frontend

The `frontend/vercel.json` rewrite sends SPA routes to `index.html`, so direct
loads of routes such as `/dashboard` continue to work after deployment.

1. Create a Vercel project for this repository.
2. Set the project **Root Directory** to `frontend`.
3. Use `npm run build` as the build command and `dist` as the output
   directory. Vercel installs dependencies from the checked-in
   `frontend/package-lock.json`.
4. Set the Vercel environment variable **`VITE_API_URL`** to the public Render
   backend origin, for example:

   ```text
   VITE_API_URL=https://employee-tracker-api.onrender.com
   ```

   Vercel embeds `VITE_API_URL` at build time, so redeploy after changing it.
5. After Vercel assigns the final frontend URL, update Render's `CORS_ORIGINS`
   JSON array to that exact `https://` origin and redeploy the backend if
   needed.

The frontend template is available at
[`frontend/.env.example`](frontend/.env.example). Do not commit a populated
`.env` file.

## Docker Compose

Docker Compose remains the supported all-in-one deployment path. Copy the
root environment template, populate its secrets and URLs, then run:

```sh
cp .env.example .env
docker compose config --quiet
docker compose up -d --build --remove-orphans
docker compose ps
curl --fail http://localhost:8080/health
```

For the full Compose configuration, TLS termination guidance, migrations,
tests, and self-managed deployment procedure, see [`README.md`](README.md).

## Local validation

Run the repository checks before deploying:

```sh
make test
make lint
make build
```

The Vercel configuration can be validated without installing another package:

```sh
node -e "JSON.parse(require('fs').readFileSync('frontend/vercel.json', 'utf8')); console.log('frontend/vercel.json: valid JSON')"
```

Validate the Render Blueprint with the Render CLI when it is installed:

```sh
render blueprints validate render.yaml
```

The Render CLI performs schema validation in addition to basic YAML parsing and
is the authoritative check for Blueprint fields such as service plans and
Docker paths.
