import os

from google.api_core.client_options import ClientOptions
from google.cloud import documentai_v1 as documentai
from google.cloud import storage

from .application import get_document_record
from .documents import (
    mark_document_failed,
    mark_document_processed,
    mark_document_processing,
)
from .models import DocumentType


def process_document_with_document_ai(
    application_id: str,
    document_type: DocumentType,
) -> dict:
    """OCR one received document and persist extracted text for validation."""
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("DOCAI_LOCATION", "us")
    processor_id = os.environ.get("DOCAI_PROCESSOR_ID")
    bucket_name = os.environ.get("UPLOAD_BUCKET")

    missing = [
        name
        for name, value in (
            ("GOOGLE_CLOUD_PROJECT", project_id),
            ("DOCAI_PROCESSOR_ID", processor_id),
            ("UPLOAD_BUCKET", bucket_name),
        )
        if not value
    ]
    if missing:
        raise ValueError(
            f"Document processing configuration missing: {', '.join(missing)}."
        )

    record = get_document_record(application_id, document_type)
    if not record.storage_path:
        raise ValueError("Document must be received before it can be processed.")

    mark_document_processing(application_id, document_type)

    try:
        blob = storage.Client().bucket(bucket_name).blob(record.storage_path)
        content = blob.download_as_bytes()
        mime_type = record.content_type or "application/pdf"
        endpoint = f"{location}-documentai.googleapis.com"
        client = documentai.DocumentProcessorServiceClient(
            client_options=ClientOptions(api_endpoint=endpoint)
        )
        processor_name = client.processor_path(
            project_id,
            location,
            processor_id,
        )
        result = client.process_document(
            request=documentai.ProcessRequest(
                name=processor_name,
                raw_document=documentai.RawDocument(
                    content=content,
                    mime_type=mime_type,
                ),
            )
        )
        extracted_data = {
            "text": result.document.text[:50000],
            "page_count": len(result.document.pages),
        }
        processed = mark_document_processed(
            application_id,
            document_type,
            extracted_data,
        )
        return processed.model_dump(mode="json")
    except Exception as exc:
        mark_document_failed(application_id, document_type, str(exc))
        raise RuntimeError("Document AI processing failed.") from exc
