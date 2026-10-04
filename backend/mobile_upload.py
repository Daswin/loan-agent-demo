import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any


_MEMORY_SESSIONS: dict[str, dict[str, Any]] = {}
SESSION_TTL_MINUTES = 5


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _session_key(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _firestore_collection():
    if os.environ.get("APPLICATION_STORE", "memory").lower() != "firestore":
        return None
    from google.cloud import firestore

    return firestore.Client().collection("mobile_upload_sessions")


def create_mobile_upload_session(
    application_id: str,
    document_type: str,
) -> tuple[str, dict[str, Any]]:
    token = secrets.token_urlsafe(32)
    key = _session_key(token)
    session = {
        "application_id": application_id,
        "document_type": document_type,
        "created_at": _now(),
        "expires_at": _now() + timedelta(minutes=SESSION_TTL_MINUTES),
        "upload_started": False,
        "completed": False,
        "filename": None,
        "error": None,
    }
    collection = _firestore_collection()
    if collection is None:
        _MEMORY_SESSIONS[key] = session
    else:
        collection.document(key).set(session)
    return token, session


def get_mobile_upload_session(token: str) -> dict[str, Any] | None:
    if not token:
        return None
    key = _session_key(token)
    collection = _firestore_collection()
    if collection is None:
        session = _MEMORY_SESSIONS.get(key)
    else:
        snapshot = collection.document(key).get()
        session = snapshot.to_dict() if snapshot.exists else None
    if session and session["expires_at"] <= _now() and not session["completed"]:
        session = {**session, "expired": True}
    return session


def update_mobile_upload_session(token: str, **changes) -> dict[str, Any]:
    session = get_mobile_upload_session(token)
    if session is None:
        raise ValueError("The mobile upload session was not found.")
    if session.get("expired"):
        raise ValueError("The mobile upload session has expired.")
    updated = {**session, **changes}
    updated.pop("expired", None)
    key = _session_key(token)
    collection = _firestore_collection()
    if collection is None:
        _MEMORY_SESSIONS[key] = updated
    else:
        collection.document(key).set(updated)
    return updated


def clear_memory_sessions() -> None:
    _MEMORY_SESSIONS.clear()
