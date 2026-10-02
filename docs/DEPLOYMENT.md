# Deployment guide

ArcLine is local-first because its default language model runs in Ollama and its
licensed source snapshot is downloaded by the data pipeline rather than stored
in Git. The application containers are production builds, but publishing a live
instance requires an explicit data and model policy.

## Mode 1: private local stack

This is the reference configuration in `docker-compose.yml`:

1. PostgreSQL stores the normalized fixed snapshot.
2. FastAPI runs migrations and exposes health, coverage, query, analytics, and
   evidence endpoints.
3. The Angular production bundle is served by unprivileged Nginx.
4. Ollama runs on the host. High-confidence deterministic questions continue to
   work if it is unavailable; ambiguous wording receives a specific refusal.

The services bind to loopback only. This keeps the database and API off the
public network by default.

## Mode 2: hosted portfolio demo

A hosted deployment should provide:

- managed PostgreSQL restored by `ingestion.load_postgres` from locally
  validated normalized files;
- the backend container with `DATABASE_URL`, `ALLOWED_ORIGINS`, and an explicit
  intent-model endpoint/model configured;
- the frontend container with `window.__NBA_ANALYTICS_CONFIG__.apiBaseUrl`
  pointed at the public HTTPS API;
- TLS, provider health checks, resource limits, log retention, and database
  backups.

Do not expose the development database port publicly. Do not add downloaded
third-party rows, credentials, or provider secrets to Git. Review the source
dataset's license and hosting terms before redistributing any rows through a
public service.

## Pre-release checklist

```bash
make verify
docker compose up --build -d
python3 scripts/ci_smoke.py
make language-eval
```

Then confirm that `/health`, `/api/v1/coverage`, the API documentation, one SQL
answer, one evidence drill-down, and one coverage refusal all work through the
deployed URLs.
