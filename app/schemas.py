from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from app.models import Role, Category, Status

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    role: Role

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

class IncidentCreate(BaseModel):
    title: str = Field(min_length=4, max_length=120)
    description: str = Field(min_length=10, max_length=5000)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def coordinates_pair(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Latitude and longitude must be supplied together.")
        return self

class IncidentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=4, max_length=120)
    description: str | None = Field(default=None, min_length=10, max_length=5000)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def require_update(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")
        if "title" in self.model_fields_set and self.title is None:
            raise ValueError("Title cannot be null.")
        if "description" in self.model_fields_set and self.description is None:
            raise ValueError("Description cannot be null.")
        return self

class IncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str
    category: Category
    status: Status
    latitude: float | None
    longitude: float | None
    ai_summary: str
    ai_confidence: float | None
    ai_review_flag: bool
    reporter_id: int
    assigned_to: int | None
    created_at: datetime

class StatusUpdate(BaseModel):
    status: Status
    reason: str | None = Field(default=None, max_length=500)

class AssignRequest(BaseModel):
    coordinator_id: int

class ClassifyRequest(BaseModel):
    description: str = Field(min_length=3, max_length=5000)

class IncidentNoteCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)

class IncidentNoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    incident_id: int
    author_id: int
    content: str
    created_at: datetime

class IncidentAttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    incident_id: int
    uploader_id: int
    original_filename: str
    content_type: str
    created_at: datetime
