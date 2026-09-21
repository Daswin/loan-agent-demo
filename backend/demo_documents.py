from .application import (
    begin_document_collection,
    get_application,
)
from .documents import (
    build_storage_path,
    mark_document_processed,
    mark_document_processing,
    register_document_received,
)
from .models import ApplicationStatus, DocumentStatus


def _pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def create_demo_pdf(title: str, applicant_name: str) -> bytes:
    """Create a small valid PDF suitable for prototype upload testing."""
    lines = [
        "BT",
        "/F1 18 Tf",
        "72 720 Td",
        f"({_pdf_text(title)}) Tj",
        "0 -34 Td",
        "/F1 12 Tf",
        f"(Applicant: {_pdf_text(applicant_name)}) Tj",
        "0 -24 Td",
        "(Demo-generated document for workflow testing only.) Tj",
        "ET",
    ]
    stream = "\n".join(lines).encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"
        ),
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode())
        pdf.extend(body)
        pdf.extend(b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode()
    )
    return bytes(pdf)


def generate_and_upload_demo_documents(application_id: str, bucket) -> object:
    """Create, upload, and mark all missing demo documents as processed."""
    application = get_application(application_id)
    if application.status == ApplicationStatus.IN_PROGRESS:
        application = begin_document_collection(application_id)
    if application.status not in {
        ApplicationStatus.DOCUMENTS_REQUIRED,
        ApplicationStatus.DOCUMENTS_PROCESSING,
        ApplicationStatus.VALIDATION_REQUIRED,
    }:
        raise ValueError("Demo documents cannot be added at this workflow stage.")

    applicant_name = " ".join(
        part
        for part in (
            application.personal.first_name,
            application.personal.last_name,
        )
        if part
    ) or "Demo Applicant"

    for record in application.documents:
        if record.status == DocumentStatus.PROCESSED:
            continue
        filename = f"{record.document_type.value}_demo.pdf"
        storage_path = build_storage_path(
            application_id,
            record.document_type,
            filename,
        )
        title = record.document_type.value.replace("_", " ").title()
        bucket.blob(storage_path).upload_from_string(
            create_demo_pdf(title, applicant_name),
            content_type="application/pdf",
        )
        register_document_received(
            application_id,
            record.document_type,
            filename,
            "application/pdf",
        )
        mark_document_processing(application_id, record.document_type)
        mark_document_processed(
            application_id,
            record.document_type,
            {
                "demo_generated": True,
                "applicant_name": applicant_name,
                "document_title": title,
            },
        )
        application = get_application(application_id)
    return application
