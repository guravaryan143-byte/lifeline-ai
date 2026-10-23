"""Add indexes used by incident, history, note, and attachment queries.

Revision ID: 20261021_01
Revises: 20261020_00
"""
from alembic import op


revision = "20261021_01"
down_revision = "20261020_00"
branch_labels = None
depends_on = None


INDEXES = (
    ("ix_incident_category_status", "incidents", "category, status"),
    ("ix_incidents_reporter_created_at", "incidents", "reporter_id, created_at"),
    ("ix_incidents_assigned_to", "incidents", "assigned_to"),
    ("ix_incidents_created_at", "incidents", "created_at"),
    ("ix_status_history_incident_created_at", "status_history", "incident_id, created_at"),
    ("ix_status_history_actor_id", "status_history", "actor_id"),
    ("ix_incident_notes_incident_created_at", "incident_notes", "incident_id, created_at"),
    ("ix_incident_notes_author_id", "incident_notes", "author_id"),
    ("ix_incident_attachments_incident_created_at", "incident_attachments", "incident_id, created_at"),
    ("ix_incident_attachments_uploader_id", "incident_attachments", "uploader_id"),
)


def upgrade() -> None:
    for name, table, columns in INDEXES:
        op.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({columns})")


def downgrade() -> None:
    raise NotImplementedError(
        "The application index migration is irreversible to prevent index removal."
    )
