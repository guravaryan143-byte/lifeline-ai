# LifeLine AI Backend — MVP v2

A college competition prototype for reporting and coordinating community incidents, using PostgreSQL for local development by default. **Not an emergency service** and does not contact responders.

## What's implemented
- FastAPI + PostgreSQL/SQLAlchemy, JWT authentication and Argon2 password hashing
- Public registration always creates reporter role; coordinator/admin access is not self-service
- Incident create/list/detail/edit with reporter ownership filtering and coordinate validation
- AI analysis endpoint with a transparent keyword fallback
- Optional TF-IDF + Logistic Regression model trained from included synthetic data
- Human-review flags, duplicate suggestions (no automatic merging), coordinator assignment/status history
- Incident notes and private, authenticated image attachments (JPEG, PNG, WebP; 5 MB default limit)
- Login and registration rate limits (process-local; five logins and ten registrations per minute per client IP)
- Aggregated dashboard APIs and bounded pagination

## AI model and limitations
Run `python -m ml.train` to train a TF-IDF + Logistic Regression model using `ml/data/incidents.csv`. The CSV is synthetic educational data. Training prints precision, recall, F1 and a confusion matrix, and saves `ml/model.joblib` plus `ml/evaluation.json`. The held-out evaluation is small and does **not** demonstrate real-world performance. Model scores are uncalibrated; they are not probabilities of danger. If no model file exists, a transparent keyword fallback is used.

## Windows setup (installed PostgreSQL)
The native PostgreSQL 18 service detected on this machine is `postgresql-x64-18`; pgAdmin and command-line tools were found under `C:\Program Files\PostgreSQL\18\`. The service was running and port 5432 was reachable when checked. Verify both again in PowerShell:
```powershell
Get-Service -Name postgresql-x64-18
Test-NetConnection -ComputerName localhost -Port 5432
```
If it is stopped, start that exact service from an Administrator PowerShell:
```powershell
Start-Service -Name postgresql-x64-18
```

Creating a role or database changes PostgreSQL. Do not run these commands until you have approved creating `lifeline_app` and `lifeline_ai_dev`. Connect interactively; psql prompts privately for the PostgreSQL administrator password:
```powershell
& 'C:\Program Files\PostgreSQL\18\bin\psql.exe' -U postgres -h localhost -p 5432 -d postgres
```
At the `postgres=#` prompt:
```sql
CREATE ROLE lifeline_app LOGIN;
\password lifeline_app
CREATE DATABASE lifeline_ai_dev OWNER lifeline_app;
\q
```
Set the role password only at the `\password` prompt. If the role or database already exists, stop and inspect it rather than dropping or recreating it. Alternatively, create a login role in pgAdmin 4 and set `lifeline_ai_dev`'s owner to that role. To create a database through pgAdmin, use Databases → Create → Database and select the new role as owner.

Only after the database and role exist, prepare the local settings file from the backend folder. If `.env` already exists, inspect and edit it; do not overwrite it. Copy the template only when `.env` is absent:
```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```
Edit `.env` locally. Keep `DATABASE_URL` free of a password and put the raw role password in `DATABASE_PASSWORD`; this safely supports numeric passwords and special characters without manual URL encoding. `DATABASE_PASSWORD` is a secret setting and is never printed by the connection diagnostic. Set `JWT_SECRET` to a long random value. `TEST_DATABASE_URL` is optional and must point to a separate test database; `POSTGRES_*` are only for the optional Docker Compose service. Never paste credentials into chat or commit `.env`.

The parent virtual environment can be used from the backend folder. Verify connectivity only after `.env` points to the approved development database. The diagnostic prints the connected database/user on success and never prints the password or full URL:
```powershell
& '..\.venv\Scripts\python.exe' -m app.db
```
This runs `SELECT current_database(), current_user`; the expected result is `lifeline_ai_dev` and `lifeline_app`. It checks connectivity only; it does not create tables or prove that migrations have been applied. Do not start the API until the initial schema migration has been reviewed and applied with explicit approval. An existing SQLite database is not copied or migrated.

## Optional Docker Compose setup
1. Install Python 3.13 and open a terminal in `lifeline-ai-backend` (the folder containing `requirements.txt`).
2. Install Docker Desktop and make sure it is running.
3. Create and activate a virtual environment:
   ```powershell
   py -3.13 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
4. Install dependencies:
   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```
5. Create local settings and generate a development JWT secret:
   ```powershell
   if (-not (Test-Path .env)) { Copy-Item .env.example .env }
   $secret = python -c "import secrets; print(secrets.token_urlsafe(48))"
   $dbPassword = python -c "import secrets; print(secrets.token_urlsafe(24))"
   $envText = Get-Content .env -Raw
   $envText = $envText -replace '(?m)^JWT_SECRET=.*$', "JWT_SECRET=$secret"
   $envText = $envText -replace '(?m)^POSTGRES_PASSWORD=.*$', "POSTGRES_PASSWORD=$dbPassword"
   $envText = $envText -replace '(?m)^DATABASE_PASSWORD=.*$', "DATABASE_PASSWORD=$dbPassword"
   $envText = $envText -replace '(?m)^DATABASE_URL=.*$', "DATABASE_URL=postgresql+psycopg://lifeline@127.0.0.1:5432/lifeline"
   Set-Content -Encoding utf8 .env $envText
   ```
   The checked-in `.env.example` contains placeholders, not usable credentials. The commands generate local secrets and keep them in the ignored `.env` file.
6. Start PostgreSQL and wait until it reports healthy:
   ```powershell
   docker compose up -d db
   docker compose ps
   ```
7. Optional ML training: `python -m ml.train`
8. Start the API only after the initial schema migration has been reviewed and applied with explicit approval: `python run.py`
9. Open `http://127.0.0.1:8000/docs`

Stop the API with `Ctrl+C`; stop PostgreSQL with `docker compose stop db`. PostgreSQL data persists in a named Docker volume. `docker compose down -v` permanently deletes that database volume.

If PowerShell blocks virtualenv activation, run `Set-ExecutionPolicy -Scope Process Bypass` in that terminal, then activate again.

## Linux/macOS
Install Docker and Python 3.13, then run from the backend directory:
```sh
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if [ ! -f .env ]; then cp .env.example .env; fi
```
Set local secrets in the shell before starting the database and API:
```sh
export POSTGRES_PASSWORD="$(python -c 'import secrets; print(secrets.token_urlsafe(24))')"
export DATABASE_PASSWORD="${POSTGRES_PASSWORD}"
export DATABASE_URL="postgresql+psycopg://lifeline@localhost:5432/lifeline"
export JWT_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
docker compose up -d db
docker compose ps
```
Optionally run `python -m ml.train`, then start with `python run.py`.

## Database
`DATABASE_URL` selects the database and is loaded from the backend `.env` file (an absolute project-root path) or a deployment secret manager. The default targets `lifeline_app@127.0.0.1:5432/lifeline_ai_dev`; the application accepts the raw password separately in `DATABASE_PASSWORD` and constructs a SQLAlchemy `URL` so reserved characters are not misparsed or double-encoded. If a password is embedded in `DATABASE_URL`, it must be percent-encoded. The synchronous SQLAlchemy driver is psycopg 3 and PostgreSQL connection attempts have a five-second timeout. `JWT_SECRET` is required in every environment; the application has no built-in signing-key fallback. `APP_ENV` defaults to `production`, so startup fails closed unless a strong, unique `JWT_SECRET`, PostgreSQL URL, and HTTPS non-local CORS origins are explicitly configured. For local development, explicitly set `APP_ENV=development` and a local `JWT_SECRET` in the ignored `.env` file (as in `.env.example`). API startup verifies connectivity with `SELECT 1` and does not create tables. A first schema migration is required before application data routes can work; an existing SQLite `lifeline.db` is **not** migrated or copied automatically. Set `DATABASE_URL=sqlite:///./lifeline.db` only when you intentionally want to use SQLite.

The `/health` and `/api/v1/health` endpoints run a database connectivity check and return HTTP 503 when the database is unavailable. Database URLs and credentials belong in the ignored `.env` file or deployment secret manager; do not commit them.

### Back up and restore native Windows PostgreSQL
Use the PostgreSQL 18 tools installed with the server. `pg_dump` will prompt for the application role's password if required; no password should be added to the command:
```powershell
& 'C:\Program Files\PostgreSQL\18\bin\pg_dump.exe' -h localhost -p 5432 -U lifeline_app -d lifeline_ai_dev -Fc -f .\lifeline-ai-dev.dump
& 'C:\Program Files\PostgreSQL\18\bin\pg_restore.exe' --list .\lifeline-ai-dev.dump
```
Keep the dump outside source control and in protected storage. Database backups do not include image files from `UPLOAD_DIR`; back up that directory separately. To verify a restore, first create a new, separate restore database owned by `lifeline_app`, then restore and inspect it. Do not run the create command if the target already exists:
```powershell
& 'C:\Program Files\PostgreSQL\18\bin\psql.exe' -h localhost -p 5432 -U postgres -d postgres -c 'CREATE DATABASE lifeline_restore_test OWNER lifeline_app;'
& 'C:\Program Files\PostgreSQL\18\bin\pg_restore.exe' -h localhost -p 5432 -U lifeline_app -d lifeline_restore_test .\lifeline-ai-dev.dump
& 'C:\Program Files\PostgreSQL\18\bin\psql.exe' -h localhost -p 5432 -U lifeline_app -d lifeline_restore_test -c '\dt'
```
Use a newly created restore target; never restore over `lifeline_ai_dev`. Do not drop a database or apply migrations as part of backup verification.

### Back up and restore local PostgreSQL (Docker Compose)
Run a custom-format backup from the project directory:
```powershell
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f /tmp/lifeline.dump'
docker cp "$(docker compose ps -q db):/tmp/lifeline.dump" .\lifeline-backup.dump
```
Keep the backup outside source control and copy it to protected storage. Database backups do not include image files from `UPLOAD_DIR`; back up that directory separately. To verify a restore without overwriting the configured database, restore into a **new, empty** database:
```powershell
docker cp .\lifeline-backup.dump "$(docker compose ps -q db):/tmp/lifeline-backup.dump"
docker compose exec -T db sh -c 'createdb -U "$POSTGRES_USER" lifeline_restore'
docker compose exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d lifeline_restore /tmp/lifeline-backup.dump'
```
The restore target must not already exist. Do not use `docker compose down -v` as a backup or cleanup step; it deletes the persistent database volume.

## Test
`pytest -q`

The tests cover health and API availability, registration/login and password hashing, authentication and ownership checks, classification output, incident creation/editing/pagination, notes, valid and rejected uploads, download path traversal, coordinator assignment/status transitions/history, dashboards, rate limits, URL parsing, and PostgreSQL dialect/index configuration. API tests use their own temporary SQLite database and upload directory. PostgreSQL integration tests are skipped unless `TEST_DATABASE_URL` in `.env` points to a separate database with `test` in its name (for example, `lifeline_ai_test`); they never use `DATABASE_URL` and roll back inserted test rows. Unit tests do not verify a live PostgreSQL connection.

## Schema migrations
Alembic is configured to read the database URL from `DATABASE_URL` and `DATABASE_PASSWORD`; no connection string or password is stored in `alembic.ini`, and the app does not run migrations at startup. The chain starts with `20261020_00`, which creates the model tables, enum types, constraints, and user-email index; `20261021_01` then adds the query indexes. Downgrades are disabled to prevent table, data, or index removal. The local PostgreSQL development database was inspected read-only and reports revision `20261021_01` at head; its tables, columns, and model-declared indexes were present.

Before applying the chain to another database, inspect its current tables and indexes and take and verify a backup. Generate SQL without applying it using `alembic upgrade head --sql`, review the output, and compare it with the live schema. Only apply against an explicitly selected database after approval. **Do not run this migration against an uninspected production database.** No migration command was run as part of this verification.

## API quickstart
Register:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/register -H "Content-Type: application/json" -d "{\"email\":\"reporter@example.com\",\"password\":\"DemoPassword123!\"}"
```
Login (OAuth2 form: `username` is the email):
```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login -H "Content-Type: application/x-www-form-urlencoded" -d "username=reporter@example.com&password=DemoPassword123!"
```
Use the returned access token:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/incidents -H "Authorization: Bearer YOUR_TOKEN" -H "Content-Type: application/json" -d "{\"title\":\"Blocked campus road\",\"description\":\"A large pothole is blocking the campus road near the gate.\"}"
```

## Local coordinator demo account
1. Register `coordinator@example.com` as a normal user first.
2. Stop the server.
3. Run this one-time local-only command:
```bash
python -c "from app.db import SessionLocal; from app.models import User,Role; db=SessionLocal(); u=db.query(User).filter_by(email='coordinator@example.com').first(); assert u; u.role=Role.coordinator; db.commit(); db.close(); print('Coordinator role assigned locally')"
```
Never expose role promotion as a public endpoint.

## Endpoint overview
- Auth: `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me`
- AI: `POST /api/v1/ai/classify`
- Incidents: `POST /api/v1/incidents`, `GET /api/v1/incidents`, `GET /api/v1/incidents/{id}`, `PATCH /api/v1/incidents/{id}`
- Notes: `GET/POST /api/v1/incidents/{id}/notes`
- Attachments: `GET/POST /api/v1/incidents/{id}/attachments`, `GET /api/v1/incidents/{id}/attachments/{attachment_id}`
- Coordination: `POST /api/v1/incidents/{id}/assign`, `POST /api/v1/incidents/{id}/status`, `GET /api/v1/incidents/{id}/history`, `GET /api/v1/incidents/{id}/duplicates`
- Dashboard: `/api/v1/dashboard/summary`, `/categories`, `/statuses`, `/trends`, `/locations`
- Health: `/health`, `/api/v1/health`

## Production gaps
This is a college-demo MVP, not a production or emergency service. Before production, replace the process-local rate limiter with a shared limiter, add and apply Alembic migrations for schema/index changes, verify automated database backups and restores, move uploaded files to private managed storage with retention and malware-scanning policies, and complete security, privacy, monitoring, and deployment reviews. Production mode requires a unique JWT secret of at least 32 characters and HTTPS CORS origins. Never expose role promotion as a public endpoint.
