import datetime
import os
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from google.cloud import storage
import google.auth
from google.auth.transport.requests import Request
from google.adk.runners import InMemoryRunner
from google.genai import types as genai_types
from pydantic import BaseModel, Field

from .agent import root_agent
from .application import (
    begin_document_collection,
    complete_validation,
    create_application,
    get_application,
    list_applications,
    update_application_field,
    update_application_section,
)
from .bank_api import submit_application as submit_to_bank
from .credit_bureau import record_credit_consent, run_simulated_credit_check
from .documents import (
    build_storage_path,
    mark_document_failed,
    mark_document_processed,
    mark_document_processing,
    register_document_received,
)
from .document_processing import process_document_with_document_ai
from .models import CreditResult, DocumentType
from .application_data import field_label
from .form_generation import (
    generate_salary_assignment_form,
    salary_assignment_filename,
)


app = FastAPI(title="Loan Application Assistant API", version="0.3.0")
runner = InMemoryRunner(agent=root_agent, app_name="loan_agent_demo")

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "ALLOWED_ORIGINS",
        "http://localhost:8080,http://localhost:8000",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SectionUpdateRequest(BaseModel):
    values: Dict[str, Any]


class ApplicationFieldUpdateRequest(BaseModel):
    value: Any


class CreateApplicationRequest(BaseModel):
    profile_id: str | None = None
    requested_amount: float | None = None


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1)
    message: str = Field(min_length=1)
    application_id: str | None = None


class UploadUrlRequest(BaseModel):
    filename: str = Field(min_length=1)
    content_type: str = Field(min_length=1)


class DocumentReceivedRequest(UploadUrlRequest):
    pass


class DocumentProcessedRequest(BaseModel):
    extracted_data: Dict[str, Any] = Field(default_factory=dict)


class DocumentFailedRequest(BaseModel):
    error: str = Field(min_length=1)


class CreditConsentRequest(BaseModel):
    consent: bool


class CreditCheckRequest(BaseModel):
    result: CreditResult


FIELD_CHOICES = {
    "applicant.identity.primary_id.type": [
        "Driver's Licence",
        "Passport",
        "Voter's ID",
    ],
    "applicant.employment.employment_status": [
        "Salaried",
        "Self-employed",
        "Commissioned",
        "Other",
    ],
    "loan_request.loan_purpose": [
        "Home improvement",
        "Education",
        "Medical expenses",
        "Debt consolidation",
        "Other",
    ],
}

PROBLEM_MARKERS = (
    "problem",
    "issue",
    "trouble",
    "delay",
    "can't",
    "cannot",
    "won't",
    "refuse",
    "help",
)


def _quick_replies_for_field(field_path: str | None) -> list[str]:
    return FIELD_CHOICES.get(field_path or "", [])


def _is_clear_field_answer(message: str) -> bool:
    normalized = message.strip().lower()
    if not normalized or "?" in normalized:
        return False
    if any(marker in normalized for marker in PROBLEM_MARKERS):
        return False
    if normalized in {"i don't know", "not sure", "skip", "later"}:
        return False
    return len(normalized) <= 240


def _application_or_404(application_id: str):
    try:
        return get_application(application_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


def _document_type_or_422(value: str) -> DocumentType:
    try:
        return DocumentType(value)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in DocumentType)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown document type. Allowed values: {allowed}.",
        ) from exc


def _bad_request(exc: ValueError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(exc),
    )


def _generate_upload_url(blob, content_type: str) -> str:
    options = {
        "version": "v4",
        "expiration": datetime.timedelta(minutes=15),
        "method": "PUT",
        "content_type": content_type,
    }
    signer_email = os.environ.get("BACKEND_SERVICE_ACCOUNT_EMAIL")
    if signer_email:
        credentials, _ = google.auth.default()
        credentials.refresh(Request())
        options["service_account_email"] = signer_email
        options["access_token"] = credentials.token
    return blob.generate_signed_url(**options)


async def _ensure_agent_session(session_id: str) -> None:
    session = await runner.session_service.get_session(
        app_name="loan_agent_demo",
        user_id=session_id,
        session_id=session_id,
    )
    if session is None:
        await runner.session_service.create_session(
            app_name="loan_agent_demo",
            user_id=session_id,
            session_id=session_id,
        )


@app.post("/api/chat")
async def chat_endpoint(payload: ChatRequest):
    if payload.application_id:
        application = _application_or_404(payload.application_id)
    else:
        application = create_application()

    expected_field = application.completion.get("next_missing_field")
    if expected_field and _is_clear_field_answer(payload.message):
        current_application = update_application_field(
            application.application_id,
            expected_field,
            payload.message.strip(),
        )
        next_field = current_application.completion.get("next_missing_field")
        if next_field:
            reply_text = (
                "Thank you, I’ve added that. You’re making good progress. "
                f"Next, what is your {field_label(next_field)}?"
            )
        else:
            reply_text = (
                "Thank you. That completes the information portion of your "
                "application. We can now focus on the remaining documents "
                "and final checks."
            )
        return {
            "reply": reply_text,
            "application_id": current_application.application_id,
            "status": current_application.status.value,
            "quick_replies": _quick_replies_for_field(next_field),
        }

    await _ensure_agent_session(payload.session_id)
    trusted_context = (
        "<trusted_application_context>\n"
        f"application_id: {application.application_id}\n"
        f"workflow_status: {application.status.value}\n"
        f"frontend_greeting_already_shown: true\n"
        f"expected_single_field: {expected_field or 'none'}\n"
        "</trusted_application_context>\n\n"
        "<applicant_message>\n"
        f"{payload.message}\n"
        "</applicant_message>"
    )
    content = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=trusted_context)],
    )

    reply_text = ""
    async for event in runner.run_async(
        user_id=payload.session_id,
        session_id=payload.session_id,
        new_message=content,
    ):
        if not event.content or not event.content.parts:
            continue
        if hasattr(event, "is_final_response") and not event.is_final_response():
            continue
        reply_text = "".join(
            part.text or ""
            for part in event.content.parts
            if getattr(part, "text", None)
        )

    current_application = get_application(application.application_id)
    return {
        "reply": reply_text,
        "application_id": current_application.application_id,
        "status": current_application.status.value,
        "quick_replies": _quick_replies_for_field(
            current_application.completion.get("next_missing_field")
        ),
    }


@app.post("/api/applications", status_code=status.HTTP_201_CREATED)
async def create_application_endpoint(
    payload: CreateApplicationRequest | None = None,
):
    try:
        return create_application(
            profile_id=payload.profile_id if payload else None,
            requested_amount=payload.requested_amount if payload else None,
        )
    except ValueError as exc:
        raise _bad_request(exc) from exc


@app.get("/api/applications")
async def list_applications_endpoint():
    return {"applications": list_applications()}


@app.get("/api/applications/{application_id}")
async def get_application_endpoint(application_id: str):
    return _application_or_404(application_id)


@app.patch("/api/applications/{application_id}/sections/{section_name}")
async def update_section_endpoint(
    application_id: str,
    section_name: str,
    payload: SectionUpdateRequest,
):
    _application_or_404(application_id)
    try:
        return update_application_section(
            application_id,
            section_name,
            payload.values,
        )
    except ValueError as exc:
        raise _bad_request(exc) from exc


@app.patch("/api/applications/{application_id}/fields/{field_path:path}")
async def update_field_endpoint(
    application_id: str,
    field_path: str,
    payload: ApplicationFieldUpdateRequest,
):
    _application_or_404(application_id)
    try:
        return update_application_field(application_id, field_path, payload.value)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@app.post("/api/applications/{application_id}/documents/start")
async def begin_documents_endpoint(application_id: str):
    _application_or_404(application_id)
    try:
        return begin_document_collection(application_id)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@app.get(
    "/api/applications/{application_id}/documents/"
    "salary_assignment_form/template",
    response_class=HTMLResponse,
)
async def salary_assignment_template_endpoint(application_id: str):
    application = _application_or_404(application_id)
    try:
        content = generate_salary_assignment_form(application)
    except ValueError as exc:
        raise _bad_request(exc) from exc
    return HTMLResponse(
        content=content,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{salary_assignment_filename(application)}"'
            )
        },
    )


@app.post(
    "/api/applications/{application_id}/documents/{document_type}/upload-url"
)
async def create_upload_url_endpoint(
    application_id: str,
    document_type: str,
    payload: UploadUrlRequest,
):
    _application_or_404(application_id)
    typed_document = _document_type_or_422(document_type)
    bucket_name = os.environ.get("UPLOAD_BUCKET")

    if not bucket_name:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="UPLOAD_BUCKET is not configured.",
        )

    try:
        object_path = build_storage_path(
            application_id,
            typed_document,
            payload.filename,
        )
    except ValueError as exc:
        raise _bad_request(exc) from exc

    blob = storage.Client().bucket(bucket_name).blob(object_path)
    url = _generate_upload_url(blob, payload.content_type)
    return {
        "url": url,
        "gcs_uri": f"gs://{bucket_name}/{object_path}",
        "storage_path": object_path,
        "document_type": typed_document.value,
    }


@app.post(
    "/api/applications/{application_id}/documents/{document_type}/received"
)
async def document_received_endpoint(
    application_id: str,
    document_type: str,
    payload: DocumentReceivedRequest,
):
    _application_or_404(application_id)
    typed_document = _document_type_or_422(document_type)
    try:
        expected_path = build_storage_path(
            application_id,
            typed_document,
            payload.filename,
        )
        bucket_name = os.environ.get("UPLOAD_BUCKET")
        if bucket_name:
            blob = storage.Client().bucket(bucket_name).blob(expected_path)
            if not blob.exists():
                raise ValueError(
                    "The uploaded Cloud Storage object could not be verified."
                )
        return register_document_received(
            application_id,
            typed_document,
            payload.filename,
            payload.content_type,
        )
    except ValueError as exc:
        raise _bad_request(exc) from exc


@app.post(
    "/api/applications/{application_id}/documents/{document_type}/process"
)
async def process_document_endpoint(
    application_id: str,
    document_type: str,
):
    _application_or_404(application_id)
    typed_document = _document_type_or_422(document_type)
    try:
        return process_document_with_document_ai(
            application_id,
            typed_document,
        )
    except ValueError as exc:
        raise _bad_request(exc) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@app.post(
    "/api/applications/{application_id}/documents/{document_type}/processing"
)
async def document_processing_endpoint(
    application_id: str,
    document_type: str,
):
    _application_or_404(application_id)
    typed_document = _document_type_or_422(document_type)
    try:
        return mark_document_processing(application_id, typed_document)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@app.post(
    "/api/applications/{application_id}/documents/{document_type}/processed"
)
async def document_processed_endpoint(
    application_id: str,
    document_type: str,
    payload: DocumentProcessedRequest,
):
    _application_or_404(application_id)
    typed_document = _document_type_or_422(document_type)
    try:
        return mark_document_processed(
            application_id,
            typed_document,
            payload.extracted_data,
        )
    except ValueError as exc:
        raise _bad_request(exc) from exc


@app.post(
    "/api/applications/{application_id}/documents/{document_type}/failed"
)
async def document_failed_endpoint(
    application_id: str,
    document_type: str,
    payload: DocumentFailedRequest,
):
    _application_or_404(application_id)
    typed_document = _document_type_or_422(document_type)
    try:
        return mark_document_failed(
            application_id,
            typed_document,
            payload.error,
        )
    except ValueError as exc:
        raise _bad_request(exc) from exc


@app.post("/api/applications/{application_id}/credit-consent")
async def credit_consent_endpoint(
    application_id: str,
    payload: CreditConsentRequest,
):
    _application_or_404(application_id)
    return record_credit_consent(application_id, payload.consent)


@app.post("/api/applications/{application_id}/credit-check")
async def credit_check_endpoint(
    application_id: str,
    payload: CreditCheckRequest,
):
    _application_or_404(application_id)
    try:
        return run_simulated_credit_check(application_id, payload.result)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@app.post("/api/applications/{application_id}/validate")
async def validate_application_endpoint(application_id: str):
    _application_or_404(application_id)
    try:
        return complete_validation(application_id)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@app.post("/api/applications/{application_id}/submit")
async def submit_application_endpoint(application_id: str):
    _application_or_404(application_id)
    try:
        return submit_to_bank(application_id)
    except ValueError as exc:
        raise _bad_request(exc) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The bank submission failed.",
        ) from exc


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
