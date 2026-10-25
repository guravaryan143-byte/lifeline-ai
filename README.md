# LifeLine AI

LifeLine AI is an educational incident-reporting and coordination prototype. It pairs a React web interface with a FastAPI service and PostgreSQL database. **It is not an emergency service and does not contact emergency responders.**

## Features

- Reporter registration and login, with JWT authentication and Argon2 password hashing.
- Incident reporting, ownership-aware listings and updates, coordinator assignment, status history, and notes.
- Authenticated image attachments with JPEG, PNG, and WebP validation and a 5 MB default limit.
- Dashboard summaries, incident classification, human-review flags, and duplicate suggestions.
- Optional TF-IDF and Logistic Regression model trained on the included synthetic dataset; a transparent keyword fallback is used when no model artifact is present.
- Alembic schema migrations and bounded API pagination.

Classification is decision support only. Model scores are uncalibrated and must not be interpreted as probabilities of danger. The included synthetic dataset and small held-out evaluation do not demonstrate real-world performance.

## Screenshots

No screenshots are included yet. Add genuine, privacy-safe screenshots here when available; do not use real incident or user data.

## Technology and architecture

| Layer | Technologies |
| --- | --- |
| Frontend | React 18, TypeScript, Vite, React Router, Axios, Recharts |
| API | Python 3.13, FastAPI, Pydantic Settings |
| Persistence | PostgreSQL, SQLAlchemy 2, psycopg 3, Alembic |
| Authentication | JWT and Argon2 password hashing |
| Classification | scikit-learn TF-IDF and Logistic Regression, with a keyword fallback |
| Tests | pytest, FastAPI TestClient, temporary SQLite databases |

The browser UI in `life-line-ai frontend/lifeline-ai-frontend` calls the FastAPI API; it never connects directly to PostgreSQL. API routes and request handling are in `app/main.py`, persistence and models are in `app/db.py` and `app/models.py`, business and classification logic is in `app/services.py`, and schema changes are in `migrations/`.

## Requirements

- Python 3.13
- Node.js 20+ and npm
- PostgreSQL 17+ or Docker Desktop with Docker Compose

## Local development

Run backend commands from the repository root (the directory containing `requirements.txt`) unless a step says otherwise.

### 1. Set up PostgreSQL and Python

Create a local PostgreSQL database and role, or use the optional Compose service below. Copy the sample settings only if you do not already have a `.env` file:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Edit `.env` locally. Set a unique `JWT_SECRET`, a strong `POSTGRES_PASSWORD` and `DATABASE_PASSWORD`, and ensure `DATABASE_URL` points to the database and role configured for your local environment. `DATABASE_PASSWORD` is the raw database password; it is kept separate from the URL. Never commit `.env` or put secrets in frontend `VITE_` variables.

Create an environment and install Python dependencies:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

For Linux/macOS, use `python3.13 -m venv .venv` and `source .venv/bin/activate`.

After confirming that `DATABASE_URL` selects the intended development database, apply its schema and start the API:

```powershell
alembic upgrade head
python run.py
```

The API listens on `http://127.0.0.1:8000`. Interactive API documentation is at `http://127.0.0.1:8000/docs`; health checks are at `/health` and `/api/v1/health`. The application does not apply migrations at startup.

### Optional PostgreSQL with Docker Compose

The Compose service uses the `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` values from `.env`. Make `DATABASE_URL` and `DATABASE_PASSWORD` match those same values before starting it. The sample Compose values use database/user `lifeline` and require you to replace the password placeholder.

```powershell
docker compose up -d db
docker compose ps
```

Wait for the database health check to pass, then apply the schema and run the API as above. Stop the service with `docker compose stop db`. Its data persists in a named volume; `docker compose down -v` permanently deletes that volume.

### 2. Start the frontend

In a second terminal, change to `life-line-ai frontend/lifeline-ai-frontend`:

```powershell
npm ci
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
npm run dev
```

The frontend runs at `http://127.0.0.1:5173`. `VITE_API_BASE_URL` in the frontend `.env` is public browser configuration and should contain only the API base URL, never a password, database URL with credentials, or signing key. Configure the backend `CORS_ORIGINS` to include the frontend origin.

## Configuration

Backend settings are loaded from the project-root `.env` file or the process environment. `.env.example` lists the supported values:

| Variable | Purpose |
| --- | --- |
| `APP_NAME` | API display name |
| `APP_ENV` | `development` or `production`; production is the default if not set |
| `DATABASE_URL` | SQLite or PostgreSQL+psycopg database URL |
| `DATABASE_PASSWORD` | Optional raw PostgreSQL password, separate from the URL |
| `TEST_DATABASE_URL` | Optional separate PostgreSQL integration-test database |
| `JWT_SECRET` | Required signing secret; production requires a unique value of at least 32 characters |
| `JWT_EXPIRE_MINUTES` | Access-token lifetime |
| `CORS_ORIGINS` | Comma-separated explicit browser origins; production requires HTTPS non-local origins |
| `UPLOAD_DIR` | Local attachment storage directory |
| `MAX_UPLOAD_SIZE_MB` | Attachment size limit |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Credentials/settings for the optional Compose database only |

Production deployments must use a secret manager or private environment configuration, HTTPS, exact CORS origins, private durable attachment storage, shared rate limiting, monitoring, and verified backup/restore procedures. The current process-local rate limiter and local-disk attachment storage are prototype limitations.

## API overview

The complete interactive schema is available at `/docs` while the API is running.

| Area | Routes |
| --- | --- |
| Authentication | `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me` |
| Classification | `POST /api/v1/ai/classify` |
| Incidents | `POST/GET /api/v1/incidents`, `GET/PATCH /api/v1/incidents/{id}` |
| Notes and attachments | `GET/POST /api/v1/incidents/{id}/notes`, `GET/POST /api/v1/incidents/{id}/attachments`, `GET /api/v1/incidents/{id}/attachments/{attachment_id}` |
| Coordination | `POST /api/v1/incidents/{id}/assign`, `POST /api/v1/incidents/{id}/status`, `GET /api/v1/incidents/{id}/history`, `GET /api/v1/incidents/{id}/duplicates` |
| Dashboard | `/api/v1/dashboard/summary`, `/categories`, `/statuses`, `/trends`, `/locations` |
| Health | `GET /health`, `GET /api/v1/health` |

Public registration always assigns the reporter role. Coordinator/admin permissions are not self-service; the API is authoritative for authorization.

## Machine learning

The training data in `ml/data/incidents.csv` is synthetic educational data. To train and evaluate the optional model:

```powershell
python -m ml.train
```

This writes generated `ml/model.joblib` and `ml/evaluation.json` files. The model binary is ignored by Git; evaluation output is included in the repository.

## Tests and build

Backend tests use isolated temporary SQLite databases and do not require a live PostgreSQL service:

```powershell
python -m pytest -q
```

PostgreSQL integration tests are skipped unless `TEST_DATABASE_URL` points to a separate test database. Do not use production data for tests.

Frontend type-check and production build:

```powershell
Set-Location 'life-line-ai frontend/lifeline-ai-frontend'
npm ci
npm run typecheck
npm run build
```

## Deployment notes

Build the frontend with `VITE_API_BASE_URL` set to the public HTTPS API origin. Configure the API with the exact deployed frontend origin in `CORS_ORIGINS`; serve the frontend `index.html` as a fallback for client-side routes. Keep database credentials and JWT signing keys out of the built frontend. Review and apply migrations only to the intended database, and never run migrations against a production database without first reviewing the target and a verified backup.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for development checks and contribution guidance.

## License

This project is licensed under the Apache License 2.0. See [LICENSE](./LICENSE).

## Project status

This is an educational MVP, not a production-ready emergency response system. It does not contact responders, and it must not be relied on for emergency decisions. Production use requires further security, privacy, operational, and domain-expert review.
