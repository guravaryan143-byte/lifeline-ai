from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.core.config import settings
from app.db import engine, get_db
from app.models import User, Role, Incident, Status, StatusHistory, Category, IncidentNote, IncidentAttachment
from app.schemas import UserCreate, UserOut, TokenOut, IncidentCreate, IncidentUpdate, IncidentOut, StatusUpdate, AssignRequest, ClassifyRequest, IncidentNoteCreate, IncidentNoteOut, IncidentAttachmentOut
from app.security import hash_password, verify_password, create_access_token, get_current_user, require_roles
from app.services import analyze_description, duplicate_candidates
from app.rate_limit import login_rate_limit, register_rate_limit

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        engine.dispose()
        raise RuntimeError(
            "Database connection failed. Check DATABASE_URL and PostgreSQL availability."
        ) from None
    try:
        yield
    finally:
        engine.dispose()

app = FastAPI(title=settings.app_name, version="0.1.0", description="Community incident coordination prototype. Not an emergency service.", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in settings.cors_origins.split(",") if x.strip()],
                   allow_credentials=True, allow_methods=["GET", "POST", "PATCH"], allow_headers=["Authorization", "Content-Type"])

@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database unavailable") from None
    return {"status": "ok", "service": "LifeLine AI", "emergency_service": False}

@app.get("/api/v1/health")
def api_health(db: Session = Depends(get_db)):
    return health(db)

@app.post("/api/v1/auth/register", response_model=UserOut, status_code=201, dependencies=[Depends(register_rate_limit)])
def register(payload: UserCreate, db: Session = Depends(get_db)):
    email = payload.email.lower()
    if db.query(User).filter(func.lower(User.email) == email).first():
        raise HTTPException(409, "Email is already registered")
    user = User(email=email, password_hash=hash_password(payload.password), role=Role.reporter)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if db.query(User).filter(func.lower(User.email) == email).first():
            raise HTTPException(409, "Email is already registered") from None
        raise
    db.refresh(user)
    return user

@app.post("/api/v1/auth/login", response_model=TokenOut, dependencies=[Depends(login_rate_limit)])
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(func.lower(User.email) == form.username.lower()).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password", headers={"WWW-Authenticate": "Bearer"})
    return {"access_token": create_access_token(user.id), "token_type": "bearer"}

@app.get("/api/v1/auth/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user

@app.post("/api/v1/ai/classify")
def classify(payload: ClassifyRequest, user: User = Depends(get_current_user)):
    result = analyze_description(payload.description)
    result["category"] = result["category"].value
    return result

@app.post("/api/v1/incidents", response_model=IncidentOut, status_code=201)
def create_incident(payload: IncidentCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    analysis = analyze_description(payload.description)
    incident = Incident(title=payload.title, description=payload.description,
        latitude=payload.latitude, longitude=payload.longitude, reporter_id=user.id,
        category=analysis["category"], ai_summary=analysis["summary"],
        ai_confidence=analysis["confidence"], ai_review_flag=analysis["review_required"])
    db.add(incident); db.commit(); db.refresh(incident)
    return incident

@app.get("/api/v1/incidents", response_model=list[IncidentOut])
def list_incidents(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    category: Category | None = None, status: Status | None = None,
    db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(Incident)
    if user.role == Role.reporter:
        query = query.filter(Incident.reporter_id == user.id)
    if category: query = query.filter(Incident.category == category)
    if status: query = query.filter(Incident.status == status)
    return query.order_by(Incident.created_at.desc()).offset((page-1)*page_size).limit(page_size).all()

@app.get("/api/v1/incidents/{incident_id}", response_model=IncidentOut)
def get_incident(incident_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.get(Incident, incident_id)
    if not item: raise HTTPException(404, "Incident not found")
    if user.role == Role.reporter and item.reporter_id != user.id: raise HTTPException(403, "Not your incident")
    return item

@app.patch("/api/v1/incidents/{incident_id}", response_model=IncidentOut)
def update_incident(incident_id: int, payload: IncidentUpdate, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    item = db.get(Incident, incident_id)
    if not item: raise HTTPException(404, "Incident not found")
    if user.role == Role.reporter and (item.reporter_id != user.id or item.status != Status.reported):
        raise HTTPException(403, "Only the reporter may edit their incident while it is reported")
    updates = payload.model_dump(exclude_unset=True)
    latitude = updates.get("latitude", item.latitude)
    longitude = updates.get("longitude", item.longitude)
    if (latitude is None) != (longitude is None):
        raise HTTPException(422, "Latitude and longitude must be supplied together.")
    for field, value in updates.items():
        setattr(item, field, value)
    if "description" in updates:
        analysis = analyze_description(item.description)
        item.category = analysis["category"]
        item.ai_summary = analysis["summary"]
        item.ai_confidence = analysis["confidence"]
        item.ai_review_flag = analysis["review_required"]
    db.commit(); db.refresh(item)
    return item

@app.get("/api/v1/incidents/{incident_id}/notes", response_model=list[IncidentNoteOut])
def list_incident_notes(incident_id: int, db: Session = Depends(get_db),
                        user: User = Depends(get_current_user)):
    item = db.get(Incident, incident_id)
    if not item: raise HTTPException(404, "Incident not found")
    if user.role == Role.reporter and item.reporter_id != user.id: raise HTTPException(403, "Not your incident")
    return db.query(IncidentNote).filter_by(incident_id=incident_id).order_by(IncidentNote.created_at).all()

@app.post("/api/v1/incidents/{incident_id}/notes", response_model=IncidentNoteOut, status_code=201)
def add_incident_note(incident_id: int, payload: IncidentNoteCreate, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    item = db.get(Incident, incident_id)
    if not item: raise HTTPException(404, "Incident not found")
    if user.role == Role.reporter and item.reporter_id != user.id: raise HTTPException(403, "Not your incident")
    note = IncidentNote(incident_id=incident_id, author_id=user.id, content=payload.content)
    db.add(note); db.commit(); db.refresh(note)
    return note

def _attachment_for_user(incident_id: int, attachment_id: int, db: Session, user: User):
    item = db.get(Incident, incident_id)
    if not item: raise HTTPException(404, "Incident not found")
    if user.role == Role.reporter and item.reporter_id != user.id: raise HTTPException(403, "Not your incident")
    attachment = db.get(IncidentAttachment, attachment_id)
    if not attachment or attachment.incident_id != incident_id:
        raise HTTPException(404, "Attachment not found")
    return attachment


def _attachment_storage_path(storage_key: str) -> Path | None:
    if not storage_key or Path(storage_key).name != storage_key or "/" in storage_key or "\\" in storage_key:
        return None
    upload_dir = Path(settings.upload_dir).resolve()
    stored_path = (upload_dir / storage_key).resolve()
    if stored_path.parent != upload_dir:
        return None
    return stored_path


@app.get("/api/v1/incidents/{incident_id}/attachments", response_model=list[IncidentAttachmentOut])
def list_incident_attachments(incident_id: int, db: Session = Depends(get_db),
                              user: User = Depends(get_current_user)):
    item = db.get(Incident, incident_id)
    if not item: raise HTTPException(404, "Incident not found")
    if user.role == Role.reporter and item.reporter_id != user.id: raise HTTPException(403, "Not your incident")
    return db.query(IncidentAttachment).filter_by(incident_id=incident_id).order_by(IncidentAttachment.created_at).all()

@app.post("/api/v1/incidents/{incident_id}/attachments", response_model=IncidentAttachmentOut, status_code=201)
def add_incident_attachment(incident_id: int, file: UploadFile = File(...),
                            db: Session = Depends(get_db),
                            user: User = Depends(get_current_user)):
    item = db.get(Incident, incident_id)
    if not item: raise HTTPException(404, "Incident not found")
    if user.role == Role.reporter and item.reporter_id != user.id: raise HTTPException(403, "Not your incident")
    allowed_types = {
        "image/jpeg": (".jpg", lambda data: data.startswith(b"\xff\xd8\xff")),
        "image/png": (".png", lambda data: data.startswith(b"\x89PNG\r\n\x1a\n")),
        "image/webp": (".webp", lambda data: len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"),
    }
    image_type = allowed_types.get(file.content_type or "")
    if not image_type:
        raise HTTPException(415, "Only JPEG, PNG, and WebP images are accepted.")
    contents = file.file.read(settings.max_upload_size_mb * 1024 * 1024 + 1)
    if len(contents) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(413, f"Image exceeds the {settings.max_upload_size_mb} MB limit.")
    extension, signature_matches = image_type
    if not signature_matches(contents):
        raise HTTPException(415, "File content does not match the declared image type.")
    original_filename = (file.filename or f"image{extension}").replace("\\", "/").split("/")[-1]
    original_filename = "".join(char for char in original_filename if char.isprintable())[:255] or f"image{extension}"
    storage_key = f"{uuid4().hex}{extension}"
    upload_dir = Path(settings.upload_dir).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_path = upload_dir / storage_key
    stored_path.write_bytes(contents)
    attachment = IncidentAttachment(
        incident_id=incident_id,
        uploader_id=user.id,
        storage_key=storage_key,
        original_filename=original_filename,
        content_type=file.content_type,
    )
    db.add(attachment)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        stored_path.unlink(missing_ok=True)
        raise
    db.refresh(attachment)
    return attachment

@app.get("/api/v1/incidents/{incident_id}/attachments/{attachment_id}")
def get_incident_attachment(incident_id: int, attachment_id: int, db: Session = Depends(get_db),
                            user: User = Depends(get_current_user)):
    attachment = _attachment_for_user(incident_id, attachment_id, db, user)
    stored_path = _attachment_storage_path(attachment.storage_key)
    if stored_path is None or not stored_path.is_file():
        raise HTTPException(404, "Attachment file is missing from storage")
    return FileResponse(
        stored_path,
        media_type=attachment.content_type,
        filename=attachment.original_filename,
        headers={"X-Content-Type-Options": "nosniff"},
    )

@app.post("/api/v1/incidents/{incident_id}/status", response_model=IncidentOut)
def update_status(incident_id: int, payload: StatusUpdate, db: Session = Depends(get_db),
                  user: User = Depends(require_roles(Role.coordinator, Role.administrator))):
    item = db.get(Incident, incident_id)
    if not item: raise HTTPException(404, "Incident not found")
    allowed = {
        Status.reported: {Status.under_review, Status.closed},
        Status.under_review: {Status.assigned, Status.in_progress, Status.closed},
        Status.assigned: {Status.in_progress, Status.closed},
        Status.in_progress: {Status.resolved, Status.closed},
        Status.resolved: {Status.closed, Status.in_progress},
        Status.closed: {Status.under_review},
    }
    if payload.status not in allowed[item.status]:
        raise HTTPException(422, f"Invalid transition: {item.status.value} -> {payload.status.value}")
    old = item.status
    item.status = payload.status
    db.add(StatusHistory(incident_id=item.id, actor_id=user.id, old_status=old.value,
                         new_status=payload.status.value, reason=payload.reason))
    db.commit(); db.refresh(item)
    return item

@app.get("/api/v1/incidents/{incident_id}/history")
def incident_history(incident_id: int, db: Session = Depends(get_db),
                     user: User = Depends(require_roles(Role.coordinator, Role.administrator))):
    if not db.get(Incident, incident_id): raise HTTPException(404, "Incident not found")
    rows = db.query(StatusHistory).filter_by(incident_id=incident_id).order_by(
        StatusHistory.created_at, StatusHistory.id
    ).all()
    return [{"old_status": r.old_status, "new_status": r.new_status, "actor_id": r.actor_id,
             "reason": r.reason, "created_at": r.created_at} for r in rows]

@app.post("/api/v1/incidents/{incident_id}/assign", response_model=IncidentOut)
def assign_incident(incident_id: int, payload: AssignRequest, db: Session = Depends(get_db),
                    user: User = Depends(require_roles(Role.coordinator, Role.administrator))):
    item = db.get(Incident, incident_id)
    if not item: raise HTTPException(404, "Incident not found")
    coordinator = db.get(User, payload.coordinator_id)
    if not coordinator or coordinator.role not in {Role.coordinator, Role.administrator}:
        raise HTTPException(422, "Target user must be a coordinator or administrator")
    old_status = item.status.value
    item.assigned_to = coordinator.id
    if item.status in {Status.reported, Status.under_review}: item.status = Status.assigned
    db.add(StatusHistory(incident_id=item.id, actor_id=user.id, old_status=old_status,
                         new_status=item.status.value, reason=f"Assigned to user {coordinator.id}"))
    db.commit(); db.refresh(item)
    return item

@app.get("/api/v1/incidents/{incident_id}/duplicates")
def duplicates(incident_id: int, db: Session = Depends(get_db),
               user: User = Depends(require_roles(Role.coordinator, Role.administrator))):
    item = db.get(Incident, incident_id)
    if not item: raise HTTPException(404, "Incident not found")
    recent = db.query(Incident).filter(Incident.id != item.id).order_by(Incident.created_at.desc()).limit(200).all()
    return duplicate_candidates(item.description, recent)

@app.get("/api/v1/dashboard/summary")
def dashboard(db: Session = Depends(get_db), user: User = Depends(require_roles(Role.coordinator, Role.administrator))):
    total = db.query(func.count(Incident.id)).scalar() or 0
    open_count = db.query(func.count(Incident.id)).filter(Incident.status.notin_([Status.resolved, Status.closed])).scalar() or 0
    resolved = db.query(func.count(Incident.id)).filter(Incident.status == Status.resolved).scalar() or 0
    review = db.query(func.count(Incident.id)).filter(Incident.ai_review_flag.is_(True)).scalar() or 0
    return {"total": total, "open": open_count, "resolved": resolved, "requiring_human_review": review}

@app.get("/api/v1/dashboard/categories")
def dashboard_categories(db: Session = Depends(get_db), user: User = Depends(require_roles(Role.coordinator, Role.administrator))):
    rows = db.query(Incident.category, func.count(Incident.id)).group_by(Incident.category).all()
    return {category.value: count for category, count in rows}

@app.get("/api/v1/dashboard/statuses")
def dashboard_statuses(db: Session = Depends(get_db), user: User = Depends(require_roles(Role.coordinator, Role.administrator))):
    rows = db.query(Incident.status, func.count(Incident.id)).group_by(Incident.status).all()
    return {status.value: count for status, count in rows}

@app.get("/api/v1/dashboard/locations")
def dashboard_locations(db: Session = Depends(get_db), user: User = Depends(require_roles(Role.coordinator, Role.administrator))):
    rows = db.query(Incident.id, Incident.title, Incident.latitude, Incident.longitude).filter(
        Incident.latitude.is_not(None), Incident.longitude.is_not(None)).limit(500).all()
    return [{"id": i, "title": t, "latitude": lat, "longitude": lon} for i, t, lat, lon in rows]

@app.get("/api/v1/dashboard/trends")
def dashboard_trends(db: Session = Depends(get_db), user: User = Depends(require_roles(Role.coordinator, Role.administrator))):
    rows = db.query(func.date(Incident.created_at), func.count(Incident.id)).group_by(func.date(Incident.created_at)).order_by(func.date(Incident.created_at)).all()
    return [{"date": str(day), "count": count} for day, count in rows]
