from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, Float, ForeignKey, Enum as SAEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base
import enum

def utcnow():
    return datetime.now(timezone.utc)

class Role(str, enum.Enum):
    reporter = "reporter"
    coordinator = "coordinator"
    administrator = "administrator"

class Category(str, enum.Enum):
    road_hazard = "road_hazard"
    medical_assistance = "medical_assistance"
    fire_environmental = "fire_environmental"
    infrastructure_damage = "infrastructure_damage"
    public_safety = "public_safety"
    other = "other"

class Status(str, enum.Enum):
    reported = "reported"
    under_review = "under_review"
    assigned = "assigned"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(SAEnum(Role), default=Role.reporter)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    incidents: Mapped[list["Incident"]] = relationship(
        back_populates="reporter",
        foreign_keys=lambda: [Incident.reporter_id],
    )

class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (
        Index("ix_incident_category_status", "category", "status"),
        Index("ix_incidents_reporter_created_at", "reporter_id", "created_at"),
        Index("ix_incidents_assigned_to", "assigned_to"),
        Index("ix_incidents_created_at", "created_at"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[Category] = mapped_column(SAEnum(Category), default=Category.other)
    status: Mapped[Status] = mapped_column(SAEnum(Status), default=Status.reported)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_summary: Mapped[str] = mapped_column(Text, default="")
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_review_flag: Mapped[bool] = mapped_column(default=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    reporter: Mapped[User] = relationship(back_populates="incidents", foreign_keys=[reporter_id])
    history: Mapped[list["StatusHistory"]] = relationship(back_populates="incident", cascade="all, delete-orphan")
    notes: Mapped[list["IncidentNote"]] = relationship(back_populates="incident", cascade="all, delete-orphan")
    attachments: Mapped[list["IncidentAttachment"]] = relationship(back_populates="incident", cascade="all, delete-orphan")

class StatusHistory(Base):
    __tablename__ = "status_history"
    __table_args__ = (
        Index("ix_status_history_incident_created_at", "incident_id", "created_at"),
        Index("ix_status_history_actor_id", "actor_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"))
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    old_status: Mapped[str] = mapped_column(String(30))
    new_status: Mapped[str] = mapped_column(String(30))
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    incident: Mapped[Incident] = relationship(back_populates="history")

class IncidentNote(Base):
    __tablename__ = "incident_notes"
    __table_args__ = (
        Index("ix_incident_notes_incident_created_at", "incident_id", "created_at"),
        Index("ix_incident_notes_author_id", "author_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"))
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    incident: Mapped[Incident] = relationship(back_populates="notes")

class IncidentAttachment(Base):
    __tablename__ = "incident_attachments"
    __table_args__ = (
        Index("ix_incident_attachments_incident_created_at", "incident_id", "created_at"),
        Index("ix_incident_attachments_uploader_id", "uploader_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"))
    uploader_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    storage_key: Mapped[str] = mapped_column(String(80), unique=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    incident: Mapped[Incident] = relationship(back_populates="attachments")
