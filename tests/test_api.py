from datetime import datetime, timedelta, timezone

from jose import jwt
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from app.core.config import settings
from app.main import app
from app.db import get_db
from app.models import Incident, IncidentAttachment, Role, User
from app.security import verify_password

def register(client, email="reporter@example.com"):
    response = client.post("/api/v1/auth/register", json={
        "email": email, "password": "DemoPassword123!"
    })
    assert response.status_code == 201, response.text
    return response.json()

def token(client, email="reporter@example.com"):
    response = client.post("/api/v1/auth/login", data={
        "username": email, "password": "DemoPassword123!"
    })
    assert response.status_code == 200, response.text
    return response.json()["access_token"]

def test_health_and_registration_login():
    with TestClient(app) as client:
        assert client.get("/health").json()["status"] == "ok"
        user = register(client)
        assert user["role"] == "reporter"
        with app.state.test_session_factory() as db:
            saved_user = db.get(User, user["id"])
            assert saved_user is not None
            assert saved_user.password_hash != "DemoPassword123!"
            assert verify_password("DemoPassword123!", saved_user.password_hash)
        access_token = token(client)
        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
        assert me.status_code == 200
        assert me.json()["email"] == "reporter@example.com"
        assert "password_hash" not in me.json()


def test_classification_requires_auth_and_returns_honest_fallback_result():
    with TestClient(app) as client:
        assert client.post(
            "/api/v1/ai/classify",
            json={"description": "There is smoke and fire near the building."},
        ).status_code == 401

        register(client)
        headers = {"Authorization": f"Bearer {token(client)}"}
        response = client.post(
            "/api/v1/ai/classify",
            headers=headers,
            json={"description": "There is smoke and fire near the building."},
        )

        assert response.status_code == 200
        result = response.json()
        assert result["category"] == "fire_environmental"
        assert result["review_required"] is True
        assert result["confidence"] is None
        assert result["method"] == "keyword_fallback"


def test_bad_login_and_protected_route():
    with TestClient(app) as client:
        register(client)
        bad = client.post("/api/v1/auth/login", data={
            "username": "reporter@example.com", "password": "wrong-password"
        })
        assert bad.status_code == 401
        assert client.get("/api/v1/incidents").status_code == 401


def test_current_user_rejects_malformed_and_expired_tokens():
    expired_token = jwt.encode(
        {
            "sub": "1",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
    with TestClient(app) as client:
        for token_value in ("not-a-jwt", expired_token):
            response = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token_value}"},
            )
            assert response.status_code == 401
            assert response.json() == {"detail": "Invalid or expired credentials"}


def test_incident_create_and_reporter_ownership():
    with TestClient(app) as client:
        register(client)
        access_token = token(client)
        headers = {"Authorization": f"Bearer {access_token}"}
        created = client.post("/api/v1/incidents", headers=headers, json={
            "title": "Road hazard near gate",
            "description": "A deep pothole is blocking the road near the campus gate.",
            "latitude": 19.076, "longitude": 72.8777
        })
        assert created.status_code == 201, created.text
        incident = created.json()
        assert incident["id"] > 0
        assert incident["category"] == "road_hazard"
        assert client.get(f"/api/v1/incidents/{incident['id']}", headers=headers).status_code == 200
        assert client.get("/api/v1/incidents", headers=headers).json()[0]["id"] == incident["id"]
        other = register(client, "other-reporter@example.com")
        other_headers = {"Authorization": "Bearer " + token(client, "other-reporter@example.com")}
        assert client.get("/api/v1/incidents", headers=other_headers).json() == []
        assert client.get(f"/api/v1/incidents/{incident['id']}",
                          headers=other_headers).status_code == 403
        assert client.post(f"/api/v1/incidents/{incident['id']}/status",
                           headers=other_headers,
                           json={"status": "closed"}).status_code == 403
        assert client.get("/api/v1/dashboard/summary",
                          headers=other_headers).status_code == 403

def test_coordinate_validation_and_duplicate_email():
    with TestClient(app) as client:
        register(client)
        duplicate = client.post("/api/v1/auth/register", json={
            "email": "REPORTER@example.com", "password": "DemoPassword123!"
        })
        assert duplicate.status_code == 409
        invalid_email = client.post("/api/v1/auth/register", json={
            "email": "not-an-email", "password": "DemoPassword123!"
        })
        assert invalid_email.status_code == 422
        access_token = token(client)
        response = client.post("/api/v1/incidents", headers={"Authorization": f"Bearer {access_token}"}, json={
            "title": "Invalid coordinate report", "description": "This report has only one coordinate.",
            "latitude": 91
        })
        assert response.status_code == 422

def test_incident_edit_notes_attachments_and_coordinator_workflow():
    with TestClient(app) as client:
        reporter = register(client)
        reporter_headers = {"Authorization": f"Bearer {token(client)}"}
        created = client.post("/api/v1/incidents", headers=reporter_headers, json={
            "title": "Road hazard near gate",
            "description": "A deep pothole is blocking the road near the campus gate.",
        })
        assert created.status_code == 201, created.text
        incident_id = created.json()["id"]

        edited = client.patch(f"/api/v1/incidents/{incident_id}", headers=reporter_headers, json={
            "title": "Updated road hazard",
            "description": "A broken pipe is leaking water beside the main building.",
        })
        assert edited.status_code == 200, edited.text
        assert edited.json()["title"] == "Updated road hazard"
        assert edited.json()["category"] == "infrastructure_damage"
        assert client.patch(f"/api/v1/incidents/{incident_id}", headers=reporter_headers,
                            json={"latitude": 19.0}).status_code == 422
        assert client.patch(f"/api/v1/incidents/{incident_id}", headers=reporter_headers,
                            json={"description": None}).status_code == 422
        coordinates = client.patch(
            f"/api/v1/incidents/{incident_id}",
            headers=reporter_headers,
            json={"latitude": 19.076, "longitude": 72.8777},
        )
        assert coordinates.status_code == 200

        note = client.post(f"/api/v1/incidents/{incident_id}/notes", headers=reporter_headers,
                           json={"content": "I added more details."})
        assert note.status_code == 201, note.text
        assert client.get(f"/api/v1/incidents/{incident_id}/notes",
                          headers=reporter_headers).json()[0]["content"] == "I added more details."

        png = b"\x89PNG\r\n\x1a\n" + b"demo image"
        uploaded = client.post(
            f"/api/v1/incidents/{incident_id}/attachments",
            headers=reporter_headers,
            files={"file": ("folder\\evidence.png", png, "image/png")},
        )
        assert uploaded.status_code == 201, uploaded.text
        attachment = uploaded.json()
        assert attachment["original_filename"] == "evidence.png"
        assert client.get(
            f"/api/v1/incidents/{incident_id}/attachments/{attachment['id']}",
            headers=reporter_headers,
        ).content == png
        assert client.get(
            f"/api/v1/incidents/{incident_id}/attachments",
            headers=reporter_headers,
        ).json()[0]["id"] == attachment["id"]

        other = register(client, "other@example.com")
        other_headers = {"Authorization": f"Bearer {token(client, 'other@example.com')}"}
        assert client.patch(f"/api/v1/incidents/{incident_id}", headers=other_headers,
                            json={"title": "Not mine"}).status_code == 403
        assert client.get(f"/api/v1/incidents/{incident_id}/notes",
                          headers=other_headers).status_code == 403
        assert client.get(
            f"/api/v1/incidents/{incident_id}/attachments/{attachment['id']}",
            headers=other_headers,
        ).status_code == 403

        coordinator = register(client, "coordinator@example.com")
        with app.state.test_session_factory() as db:
            from app.models import Role, User
            user = db.query(User).filter_by(id=coordinator["id"]).one()
            user.role = Role.coordinator
            db.commit()
        coordinator_headers = {"Authorization": f"Bearer {token(client, 'coordinator@example.com')}"}
        assignment = client.post(
            f"/api/v1/incidents/{incident_id}/assign",
            headers=coordinator_headers,
            json={"coordinator_id": coordinator["id"]},
        )
        assert assignment.status_code == 200, assignment.text
        assert assignment.json()["status"] == "assigned"
        status = client.post(
            f"/api/v1/incidents/{incident_id}/status",
            headers=coordinator_headers,
            json={"status": "in_progress", "reason": "Work started"},
        )
        assert status.status_code == 200, status.text
        assert status.json()["status"] == "in_progress"
        history = client.get(f"/api/v1/incidents/{incident_id}/history",
                             headers=coordinator_headers)
        assert history.status_code == 200
        assert [(entry["old_status"], entry["new_status"]) for entry in history.json()] == [
            ("reported", "assigned"),
            ("assigned", "in_progress"),
        ]
        assert client.get("/api/v1/dashboard/summary",
                          headers=coordinator_headers).json()["total"] == 1
        assert client.get("/api/v1/dashboard/categories",
                          headers=coordinator_headers).json() == {"infrastructure_damage": 1}
        assert client.get("/api/v1/dashboard/statuses",
                          headers=coordinator_headers).json() == {"in_progress": 1}
        locations = client.get(
            "/api/v1/dashboard/locations",
            headers=coordinator_headers,
        ).json()
        assert len(locations) == 1
        assert locations[0]["latitude"] == 19.076
        assert locations[0]["longitude"] == 72.8777
        assert len(client.get("/api/v1/dashboard/trends",
                              headers=coordinator_headers).json()) == 1
        assert client.get(f"/api/v1/incidents/{incident_id}/duplicates",
                          headers=reporter_headers).status_code == 403
        assert client.patch(f"/api/v1/incidents/{incident_id}", headers=reporter_headers,
                            json={"title": "Too late"}).status_code == 403

        duplicate = client.post("/api/v1/incidents", headers=reporter_headers, json={
            "title": "Another water leak",
            "description": "A broken pipe is leaking water beside the main building.",
        })
        assert duplicate.status_code == 201, duplicate.text
        suggestions = client.get(f"/api/v1/incidents/{incident_id}/duplicates",
                                 headers=coordinator_headers)
        assert suggestions.status_code == 200
        assert duplicate.json()["id"] in {match["incident_id"] for match in suggestions.json()}

def test_login_rate_limit():
    with TestClient(app) as client:
        for _ in range(5):
            response = client.post("/api/v1/auth/login", data={
                "username": "missing@example.com", "password": "wrong-password"
            })
            assert response.status_code == 401
        limited = client.post("/api/v1/auth/login", data={
            "username": "missing@example.com", "password": "wrong-password"
        })
        assert limited.status_code == 429
        assert int(limited.headers["Retry-After"]) > 0

def test_registration_rate_limit():
    with TestClient(app) as client:
        for index in range(10):
            response = client.post("/api/v1/auth/register", json={
                "email": f"reporter-{index}@example.com",
                "password": "DemoPassword123!",
            })
            assert response.status_code == 201, response.text
        limited = client.post("/api/v1/auth/register", json={
            "email": "reporter-11@example.com",
            "password": "DemoPassword123!",
        })
        assert limited.status_code == 429
        assert int(limited.headers["Retry-After"]) > 0

def test_health_reports_database_unavailability_without_leaking_details():
    def unavailable_database():
        class UnavailableSession:
            def execute(self, statement):
                raise SQLAlchemyError("sensitive database connection details")

            def close(self):
                pass

        yield UnavailableSession()

    original_override = app.dependency_overrides[get_db]
    app.dependency_overrides[get_db] = unavailable_database
    try:
        with TestClient(app) as client:
            response = client.get("/health")
        assert response.status_code == 503
        assert response.json() == {"detail": "Database unavailable"}
        assert "sensitive" not in response.text
    finally:
        app.dependency_overrides[get_db] = original_override


def test_attachment_download_rejects_path_traversal_in_storage_key(tmp_path):
    with TestClient(app) as client:
        reporter = register(client)
        headers = {"Authorization": f"Bearer {token(client)}"}
        incident_response = client.post(
            "/api/v1/incidents",
            headers=headers,
            json={
                "title": "Road hazard near gate",
                "description": "A deep pothole blocks the road near the campus gate.",
            },
        )
        assert incident_response.status_code == 201
        incident_id = incident_response.json()["id"]
        outside_file = tmp_path / "outside.png"
        outside_file.write_bytes(b"must not be served")

        with app.state.test_session_factory() as db:
            db.add(
                IncidentAttachment(
                    incident_id=incident_id,
                    uploader_id=reporter["id"],
                    storage_key="../outside.png",
                    original_filename="outside.png",
                    content_type="image/png",
                )
            )
            db.commit()
            attachment_id = (
                db.query(IncidentAttachment)
                .filter_by(incident_id=incident_id)
                .one()
                .id
            )

        response = client.get(
            f"/api/v1/incidents/{incident_id}/attachments/{attachment_id}",
            headers=headers,
        )
        assert response.status_code == 404
        assert response.content != outside_file.read_bytes()


def test_attachment_upload_rejects_mismatched_signature_and_oversize(monkeypatch):
    with TestClient(app) as client:
        register(client)
        headers = {"Authorization": f"Bearer {token(client)}"}
        incident_response = client.post(
            "/api/v1/incidents",
            headers=headers,
            json={
                "title": "Road hazard near gate",
                "description": "A deep pothole blocks the road near the campus gate.",
            },
        )
        incident_id = incident_response.json()["id"]

        mismatch = client.post(
            f"/api/v1/incidents/{incident_id}/attachments",
            headers=headers,
            files={"file": ("invalid.png", b"not a PNG", "image/png")},
        )
        assert mismatch.status_code == 415

        monkeypatch.setattr("app.main.settings.max_upload_size_mb", 1)
        oversized = client.post(
            f"/api/v1/incidents/{incident_id}/attachments",
            headers=headers,
            files={
                "file": (
                    "large.png",
                    b"\x89PNG\r\n\x1a\n" + b"x" * (1024 * 1024),
                    "image/png",
                )
            },
        )
        assert oversized.status_code == 413


def test_coordinator_cannot_make_invalid_status_transition_or_assign_reporter():
    with TestClient(app) as client:
        reporter = register(client)
        reporter_headers = {"Authorization": f"Bearer {token(client)}"}
        incident_response = client.post(
            "/api/v1/incidents",
            headers=reporter_headers,
            json={
                "title": "Road hazard near gate",
                "description": "A deep pothole blocks the road near the campus gate.",
            },
        )
        incident_id = incident_response.json()["id"]
        coordinator = register(client, "coordinator@example.com")

        with app.state.test_session_factory() as db:
            coordinator_user = db.get(User, coordinator["id"])
            assert coordinator_user is not None
            coordinator_user.role = Role.coordinator
            db.commit()

        coordinator_headers = {
            "Authorization": f"Bearer {token(client, 'coordinator@example.com')}"
        }
        invalid_status = client.post(
            f"/api/v1/incidents/{incident_id}/status",
            headers=coordinator_headers,
            json={"status": "resolved"},
        )
        assert invalid_status.status_code == 422

        invalid_assignment = client.post(
            f"/api/v1/incidents/{incident_id}/assign",
            headers=coordinator_headers,
            json={"coordinator_id": reporter["id"]},
        )
        assert invalid_assignment.status_code == 422

        with app.state.test_session_factory() as db:
            incident = db.get(Incident, incident_id)
            assert incident is not None
            assert incident.status.value == "reported"
            assert incident.assigned_to is None
