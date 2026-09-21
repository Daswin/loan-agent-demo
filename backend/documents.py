import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .application import get_application, save_application, utc_now
from .models import (
    ApplicationStatus,
    DocumentRecord,
    DocumentStatus,
    DocumentType,
)
from .application_data import refresh_completion


def sanitize_path_component(value: str) -> str:
    """
    Convert customer names and other values into safe path components.

    Example:
        "John Smith" -> "John_Smith"
        "Mary-Jane O'Brien" -> "Mary-Jane_O_Brien"
    """
    value = value.strip()
    value = re.sub(r"\s+", "_", value)
    value = re.sub(r"[^A-Za-z0-9_-]", "_", value)
    value = re.sub(r"_+", "_", value)

    return value.strip("_")


def get_customer_folder_name(application_id: str) -> str:
    """
    Build the customer folder from the applicant's name.

    Falls back to 'Unknown_Customer' until a name is available.
    """
    application = get_application(application_id)

    first_name = application.personal.first_name or ""
    last_name = application.personal.last_name or ""

    full_name = f"{first_name} {last_name}".strip()

    if not full_name:
        return "Unknown_Customer"

    return sanitize_path_component(full_name)


def get_document_extension(filename: str) -> str:
    """
    Return a sanitized lowercase file extension.

    Example:
        payslip.PDF -> .pdf
    """
    extension = Path(filename).suffix.lower()

    allowed_extensions = {
        ".pdf",
        ".png",
        ".jpg",
        ".jpeg",
    }

    if extension not in allowed_extensions:
        raise ValueError(
            "Unsupported document type. "
            "Allowed file extensions are PDF, PNG, JPG, and JPEG."
        )

    return extension


def build_storage_path(
    application_id: str,
    document_type: DocumentType,
    original_filename: str,
) -> str:
    """
    Build the Cloud Storage object path.

    Example:

        loan-applications/
        John_Smith/
        APP-2026-12345678/
        job_letter.pdf
    """
    customer_folder = get_customer_folder_name(
        application_id
    )

    extension = get_document_extension(
        original_filename
    )

    return (
        f"loan-applications/"
        f"{customer_folder}/"
        f"{application_id}/"
        f"{document_type.value}{extension}"
    )


def get_document_record(
    application_id: str,
    document_type: DocumentType,
) -> DocumentRecord:
    """Find a document record on an application."""
    application = get_application(application_id)

    return _find_document_record(application, document_type, application_id)


def _find_document_record(
    application,
    document_type: DocumentType,
    application_id: str,
) -> DocumentRecord:
    """Find a record on an already-loaded authoritative application."""

    for document in application.documents:
        if document.document_type == document_type:
            return document

    raise KeyError(
        f"Document '{document_type.value}' is not required "
        f"for application '{application_id}'."
    )


def register_document_received(
    application_id: str,
    document_type: DocumentType,
    original_filename: str,
    content_type: Optional[str] = None,
) -> DocumentRecord:
    """
    Register a document after it has been received/uploaded.

    This function does not upload bytes to Cloud Storage yet.
    It establishes the metadata and target storage path.
    """
    application = get_application(application_id)

    document = _find_document_record(
        application,
        document_type,
        application_id,
    )

    storage_path = build_storage_path(
        application_id,
        document_type,
        original_filename,
    )

    document.filename = original_filename
    document.storage_path = storage_path
    document.content_type = content_type
    document.status = DocumentStatus.RECEIVED
    document.received_at = utc_now()
    document.error = None

    if application.status == ApplicationStatus.DOCUMENTS_REQUIRED:
        application.status = ApplicationStatus.DOCUMENTS_PROCESSING
    elif application.status != ApplicationStatus.DOCUMENTS_PROCESSING:
        raise ValueError(
            "Documents can only be registered while documents are required "
            "or processing."
        )

    refresh_completion(application)
    save_application(application)
    return document


def mark_document_processing(
    application_id: str,
    document_type: DocumentType,
) -> DocumentRecord:
    """Mark a received document as being processed."""
    application = get_application(application_id)

    document = _find_document_record(
        application,
        document_type,
        application_id,
    )

    document.status = DocumentStatus.PROCESSING
    document.error = None

    if application.status != ApplicationStatus.DOCUMENTS_PROCESSING:
        raise ValueError(
            "Documents can only be processed while the application is in "
            "DOCUMENTS_PROCESSING."
        )

    application.updated_at = utc_now()
    refresh_completion(application)
    save_application(application)
    return document


def mark_document_processed(
    application_id: str,
    document_type: DocumentType,
    extracted_data: Optional[Dict[str, Any]] = None,
) -> DocumentRecord:
    """
    Mark document processing as successful and save
    normalized extracted information.
    """
    application = get_application(application_id)

    document = _find_document_record(
        application,
        document_type,
        application_id,
    )

    document.status = DocumentStatus.PROCESSED
    document.extracted_data = extracted_data or {}
    document.processed_at = utc_now()
    document.error = None

    application.updated_at = utc_now()

    if all(
        item.status == DocumentStatus.PROCESSED
        for item in application.documents
    ):
        application.status = ApplicationStatus.VALIDATION_REQUIRED

    refresh_completion(application)
    save_application(application)
    return document


def mark_document_failed(
    application_id: str,
    document_type: DocumentType,
    error: str,
) -> DocumentRecord:
    """Record a document-processing failure."""
    application = get_application(application_id)

    document = _find_document_record(
        application,
        document_type,
        application_id,
    )

    document.status = DocumentStatus.FAILED
    document.error = error

    application.status = ApplicationStatus.DOCUMENTS_REQUIRED

    refresh_completion(application)
    save_application(application)
    return document
