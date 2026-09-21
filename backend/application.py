from datetime import datetime, timezone
from typing import Any, Dict
from uuid import uuid4

from .models import (
    ApplicationStatus,
    DocumentRecord,
    DocumentStatus,
    DocumentType,
    LoanApplication,
)
from .repository import build_repository
from .application_data import (
    create_profile_data,
    refresh_completion,
    update_application_field as update_structured_field,
)


# ---------------------------------------------------------------------------
# Prototype application store
# ---------------------------------------------------------------------------
#
# This is intentionally in-memory for the first backend checkpoint.
#
# Once the API workflow is working end-to-end, this repository will be
# replaced by Firestore without changing the rest of the application's
# business logic.
#
_APPLICATIONS: Dict[str, LoanApplication] = {}
_REPOSITORY = build_repository(_APPLICATIONS)


_ALLOWED_STATUS_TRANSITIONS = {
    ApplicationStatus.IN_PROGRESS: {
        ApplicationStatus.DOCUMENTS_REQUIRED,
    },
    ApplicationStatus.DOCUMENTS_REQUIRED: {
        ApplicationStatus.DOCUMENTS_PROCESSING,
    },
    ApplicationStatus.DOCUMENTS_PROCESSING: {
        ApplicationStatus.DOCUMENTS_REQUIRED,
        ApplicationStatus.VALIDATION_REQUIRED,
    },
    ApplicationStatus.VALIDATION_REQUIRED: {
        ApplicationStatus.DOCUMENTS_REQUIRED,
        ApplicationStatus.READY_FOR_SUBMISSION,
    },
    ApplicationStatus.READY_FOR_SUBMISSION: {
        ApplicationStatus.SUBMITTED,
        ApplicationStatus.SUBMISSION_FAILED,
    },
    ApplicationStatus.SUBMISSION_FAILED: {
        ApplicationStatus.READY_FOR_SUBMISSION,
    },
    ApplicationStatus.SUBMITTED: set(),
}


def utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc)


def generate_application_id() -> str:
    """
    Generate a human-readable application ID.

    Example:
        APP-2026-A1B2C3D4
    """
    year = utc_now().year
    unique_part = uuid4().hex[:8].upper()

    return f"APP-{year}-{unique_part}"


def _required_documents(
    profile_id: str | None = None,
    application_data: dict[str, Any] | None = None,
) -> list[DocumentRecord]:
    """Create the initial required-document checklist."""
    document_types = [
        DocumentType.JOB_LETTER,
        DocumentType.PAYSLIP_01,
        DocumentType.SALARY_ASSIGNMENT_FORM,
    ]
    return [
        DocumentRecord(
            document_type=document_type,
            status=DocumentStatus.REQUIRED,
        )
        for document_type in document_types
    ]


def create_application(
    profile_id: str | None = None,
    requested_amount: float | None = None,
) -> LoanApplication:
    """Create and store a new loan application."""
    application_id = generate_application_id()
    now = utc_now()

    application_data = {}
    provided_fields = []
    if profile_id:
        application_data, provided_fields = create_profile_data(
            profile_id,
            requested_amount,
        )

    application = LoanApplication(
        application_id=application_id,
        status=ApplicationStatus.IN_PROGRESS,
        profile_id=profile_id,
        application_data=application_data,
        provided_fields=provided_fields,
        documents=_required_documents(profile_id, application_data),
        created_at=now,
        updated_at=now,
    )

    if profile_id:
        identity = application_data["applicant"]["identity"]
        application.personal.first_name = identity["first_name"]
        application.personal.last_name = identity["last_name"]
        application.loan.requested_amount = application_data[
            "loan_request"
        ]["requested_amount"]
    refresh_completion(application)
    _REPOSITORY.create(application)

    return application


def get_application(application_id: str) -> LoanApplication:
    """Retrieve an application or raise KeyError."""
    application = _REPOSITORY.get(application_id)

    if application is None:
        raise KeyError(
            f"Application '{application_id}' was not found."
        )

    return application


def update_application_section(
    application_id: str,
    section: str,
    values: Dict[str, Any],
) -> LoanApplication:
    """
    Update one section of an application.

    Example:

        update_application_section(
            application_id,
            "personal",
            {
                "first_name": "John",
                "last_name": "Smith",
            },
        )
    """
    application = get_application(application_id)

    allowed_sections = {
        "personal",
        "contact",
        "address",
        "physician",
        "employment",
        "income",
        "loan",
        "banking",
        "emergency_contact",
    }

    if section not in allowed_sections:
        raise ValueError(
            f"Section '{section}' cannot be updated using this method."
        )

    section_model = getattr(application, section)

    current_values = section_model.model_dump()

    unknown_fields = set(values) - set(current_values)

    if unknown_fields:
        raise ValueError(
            "Unknown field(s) for "
            f"'{section}': {', '.join(sorted(unknown_fields))}"
        )

    updated_values = {
        **current_values,
        **values,
    }

    updated_section = section_model.__class__(
        **updated_values
    )

    setattr(
        application,
        section,
        updated_section,
    )

    application.updated_at = utc_now()

    save_application(application)

    return application


def set_application_status(
    application_id: str,
    status: ApplicationStatus,
) -> LoanApplication:
    """Change status when the requested workflow transition is legal."""
    application = get_application(application_id)

    if application.status == status:
        return application

    allowed_statuses = _ALLOWED_STATUS_TRANSITIONS[application.status]

    if status not in allowed_statuses:
        raise ValueError(
            "Invalid application status transition: "
            f"{application.status.value} -> {status.value}."
        )

    application.status = status
    application.updated_at = utc_now()

    save_application(application)

    return application


def update_application_field(
    application_id: str,
    field_path: str,
    value: Any,
) -> LoanApplication:
    """Save one confirmed structured application answer."""
    application = get_application(application_id)
    update_structured_field(application, field_path, value)
    if field_path == "applicant.identity.first_name":
        application.personal.first_name = str(value)
    elif field_path == "applicant.identity.last_name":
        application.personal.last_name = str(value)
    application.updated_at = utc_now()
    save_application(application)
    return application


def begin_document_collection(application_id: str) -> LoanApplication:
    """Move a completed intake into the document-collection stage."""
    return set_application_status(
        application_id,
        ApplicationStatus.DOCUMENTS_REQUIRED,
    )


def complete_validation(application_id: str) -> LoanApplication:
    """Mark a validated package ready without making a lending decision."""
    application = get_application(application_id)

    if application.status != ApplicationStatus.VALIDATION_REQUIRED:
        raise ValueError(
            "Application must be in VALIDATION_REQUIRED before validation "
            "can be completed."
        )

    if not all_required_documents_processed(application_id):
        raise ValueError("All required documents must be processed.")

    if not application.credit_bureau.consent:
        raise ValueError("Credit bureau consent must be recorded.")

    if application.credit_bureau.result is None:
        raise ValueError("Credit bureau check must be completed.")

    return set_application_status(
        application_id,
        ApplicationStatus.READY_FOR_SUBMISSION,
    )


def get_document_record(
    application_id: str,
    document_type: DocumentType,
) -> DocumentRecord:
    """Retrieve one required document record."""
    application = get_application(application_id)

    for document in application.documents:
        if document.document_type == document_type:
            return document

    raise KeyError(
        f"Document '{document_type.value}' was not found "
        f"for application '{application_id}'."
    )


def save_application(application: LoanApplication) -> LoanApplication:
    """Persist the authoritative application after a service mutation."""
    _REPOSITORY.save(application)
    return application


def all_required_documents_processed(
    application_id: str,
) -> bool:
    """Return True when all required documents are processed."""
    application = get_application(application_id)

    return all(
        document.status == DocumentStatus.PROCESSED
        for document in application.documents
    )


def list_applications() -> list[LoanApplication]:
    """
    Return all applications.

    This is primarily useful for prototype/debugging purposes.
    """
    return _REPOSITORY.list()
