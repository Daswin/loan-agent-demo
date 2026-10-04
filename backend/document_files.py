import io
from pathlib import Path

from PIL import Image, ImageOps

from .documents import build_storage_path
from .models import DocumentType


PDF_CONTENT_TYPE = "application/pdf"
IMAGE_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png"}


def normalize_uploaded_document(
    bucket,
    application_id: str,
    document_type: DocumentType,
    original_filename: str,
    content_type: str,
) -> tuple[str, str, str]:
    """Ensure a verified upload is stored as a PDF and return its metadata."""
    source_path = build_storage_path(
        application_id,
        document_type,
        original_filename,
    )
    source_blob = bucket.blob(source_path)
    normalized_type = (content_type or "").split(";", 1)[0].strip().lower()

    if normalized_type == PDF_CONTENT_TYPE:
        if not source_blob.download_as_bytes().lstrip().startswith(b"%PDF-"):
            source_blob.delete()
            raise ValueError("The uploaded file is not a valid PDF document.")
        pdf_filename = f"{Path(original_filename).stem}.pdf"
        return pdf_filename, PDF_CONTENT_TYPE, source_path

    if normalized_type not in IMAGE_CONTENT_TYPES:
        raise ValueError("Only PDF, PNG, and JPEG documents can be uploaded.")

    try:
        image_bytes = source_blob.download_as_bytes()
        with Image.open(io.BytesIO(image_bytes)) as opened:
            image = ImageOps.exif_transpose(opened)
            if image.mode in {"RGBA", "LA"}:
                background = Image.new("RGB", image.size, "white")
                alpha = image.getchannel("A")
                background.paste(image.convert("RGB"), mask=alpha)
                image = background
            else:
                image = image.convert("RGB")
            output = io.BytesIO()
            image.save(output, format="PDF", resolution=150.0)
    except Exception as exc:
        source_blob.delete()
        raise ValueError("The uploaded image could not be converted to PDF.") from exc

    pdf_filename = f"{Path(original_filename).stem}.pdf"
    pdf_path = build_storage_path(
        application_id,
        document_type,
        pdf_filename,
    )
    bucket.blob(pdf_path).upload_from_string(
        output.getvalue(),
        content_type=PDF_CONTENT_TYPE,
    )
    if source_path != pdf_path:
        source_blob.delete()
    return pdf_filename, PDF_CONTENT_TYPE, pdf_path
