# PostgreSQL read-only review status

Date: 2026-10-21

## Inspection status

- PostgreSQL Windows service `postgresql-x64-18` is running and `localhost:5432` accepts TCP connections. This does not establish the server version or database identity.
- A fresh check after confirmation still found no project `.env` file. Pydantic resolved the fallback `postgresql+psycopg` target at `localhost:5432/lifeline`; the inspection script refused to connect because it was not `lifeline_ai_dev`.
- A second readiness confirmation produced the same sanitized configuration and was also refused; no attempt was made to connect to `lifeline`.
- The target database, environment (development/production), live PostgreSQL server version, live schema, and Alembic revision therefore remain **unverified**. No database connection, query, backup, restore, or migration was performed.
- `.env` is ignored by `.gitignore`. Configure a private URL for the dedicated `lifeline_ai_dev` database before requesting live inspection. Do not share credentials.

## Migration source review (not compared with live schema)

Migration: `migrations/versions/20261021_01_add_query_indexes.py`  
Revision: `20261021_01`; parent: none (root revision).

All ten proposed indexes are non-unique ordinary B-tree indexes, with no predicates or expressions:

| Index | Table | Columns |
|---|---|---|
| `ix_incident_category_status` | `incidents` | `category, status` |
| `ix_incidents_reporter_created_at` | `incidents` | `reporter_id, created_at` |
| `ix_incidents_assigned_to` | `incidents` | `assigned_to` |
| `ix_incidents_created_at` | `incidents` | `created_at` |
| `ix_status_history_incident_created_at` | `status_history` | `incident_id, created_at` |
| `ix_status_history_actor_id` | `status_history` | `actor_id` |
| `ix_incident_notes_incident_created_at` | `incident_notes` | `incident_id, created_at` |
| `ix_incident_notes_author_id` | `incident_notes` | `author_id` |
| `ix_incident_attachments_incident_created_at` | `incident_attachments` | `incident_id, created_at` |
| `ix_incident_attachments_uploader_id` | `incident_attachments` | `uploader_id` |

The definitions correspond to `Index` declarations in `app/models.py`. The migration issues PostgreSQL-compatible `CREATE INDEX IF NOT EXISTS` statements. The guard checks the name only; it does not verify that a same-named index has the expected definition. Its downgrade drops indexes by name, including a same-named index that may have pre-existed. Ordinary `CREATE INDEX` can block writes on the target table while it builds and consume I/O; this migration does not use `CONCURRENTLY`.

Exact generated statements:

```sql
CREATE INDEX IF NOT EXISTS ix_incident_category_status ON incidents (category, status);
CREATE INDEX IF NOT EXISTS ix_incidents_reporter_created_at ON incidents (reporter_id, created_at);
CREATE INDEX IF NOT EXISTS ix_incidents_assigned_to ON incidents (assigned_to);
CREATE INDEX IF NOT EXISTS ix_incidents_created_at ON incidents (created_at);
CREATE INDEX IF NOT EXISTS ix_status_history_incident_created_at ON status_history (incident_id, created_at);
CREATE INDEX IF NOT EXISTS ix_status_history_actor_id ON status_history (actor_id);
CREATE INDEX IF NOT EXISTS ix_incident_notes_incident_created_at ON incident_notes (incident_id, created_at);
CREATE INDEX IF NOT EXISTS ix_incident_notes_author_id ON incident_notes (author_id);
CREATE INDEX IF NOT EXISTS ix_incident_attachments_incident_created_at ON incident_attachments (incident_id, created_at);
CREATE INDEX IF NOT EXISTS ix_incident_attachments_uploader_id ON incident_attachments (uploader_id);
```

## Next gate

After configuring `.env` privately for `lifeline_ai_dev`, perform read-only identity and schema inspection first. Then create and verify a custom-format backup. Restore only into a separate, newly created test database after confirming that database does not already exist. Do not run Alembic upgrade or modify source schema without separate explicit approval.
