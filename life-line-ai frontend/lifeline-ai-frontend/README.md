# LifeLine AI frontend

React, TypeScript, and Vite frontend for the FastAPI backend in the adjacent `lifeline-ai-backend` project. The browser communicates only with FastAPI; it never connects directly to PostgreSQL.

## Local setup

Requirements: Node.js 20+ and npm. The frontend environment file is `.env` beside `package.json`:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000
```

The checked-in `.env.example` has the same non-secret value. `.env` is ignored by Git. Vite exposes `VITE_` values to browser code, so never put passwords, database URLs with credentials, or JWT secrets there. Restart Vite after changing this file.

Open two VS Code terminals:

**Terminal 1 — backend** (from the `lifeline-ai-backend` directory):

```powershell
& '.\.venv\Scripts\Activate.ps1'
python run.py
```

**Terminal 2 — frontend**:

```powershell
Set-Location 'life-line-ai frontend\lifeline-ai-frontend'
npm ci
npm run dev
```

The Vite development server binds only to `127.0.0.1:5173` and fails rather than silently moving to another port. Open `http://127.0.0.1:5173`. The backend must allow this exact CORS origin. The backend currently allows `http://127.0.0.1:5173` and `http://localhost:5173`.

Check backend health at `http://127.0.0.1:8000/health` and API documentation at `http://127.0.0.1:8000/docs`.

## Implemented backend workflows

The client uses the backend's explicit API routes and schemas, not endpoint discovery:

- Login, public reporter registration, current-user session restoration, logout, and protected routes.
- Paginated incident listing with backend status/category filters, client-side search for the current page, creation, detail retrieval, and updates.
- Coordinator/admin dashboard summary, category/status totals, location snapshot, and date trends; reporters see only their own incident feed.
- Authenticated notes, image upload/download, AI classification, and human-review notices.
- Coordinator/admin status transitions, assignment by coordinator user ID, status history, and duplicate suggestions.
- API health checks, loading states, empty states, and readable API/authorization errors.

The API is authoritative for all permissions. Reporter self-registration cannot grant coordinator or administrator roles. The bearer token is held in `sessionStorage`, which avoids long-lived persistence but remains accessible to JavaScript running in the page; prevent XSS and use HTTPS in deployment.

The backend accepts JPEG, PNG, and WebP attachments up to 5 MB. The UI validates the same limits and the backend validates them again. Classification output is decision support only, not emergency triage.

## Checks

```powershell
npm run typecheck
npm run build
```

The Python API and PostgreSQL must be available to exercise authenticated live workflows. Do not run database migrations from the frontend project. Do not use production data for testing.

## Deployment notes

Set `VITE_API_BASE_URL` at frontend build time to the HTTPS API origin; it is public browser configuration. Configure an exact production frontend origin in backend `CORS_ORIGINS`. A static host must serve `index.html` as the fallback for client-side routes. The backend's local-disk attachment storage and process-local rate limiter are prototype limitations and need durable/shared services before multi-instance production use.
