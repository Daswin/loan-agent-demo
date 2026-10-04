import io
import unittest
from unittest.mock import MagicMock

from PIL import Image

from backend import application
from backend.document_files import normalize_uploaded_document
from backend.models import DocumentType


class DocumentFileTests(unittest.TestCase):
    def setUp(self):
        application._APPLICATIONS.clear()
        self.application = application.create_application("marcus")

    def tearDown(self):
        application._APPLICATIONS.clear()

    def test_png_is_converted_to_pdf_and_original_is_removed(self):
        image_bytes = io.BytesIO()
        Image.new("RGBA", (30, 20), (40, 90, 160, 180)).save(
            image_bytes,
            format="PNG",
        )
        source_blob = MagicMock()
        source_blob.download_as_bytes.return_value = image_bytes.getvalue()
        pdf_blob = MagicMock()
        bucket = MagicMock()
        bucket.blob.side_effect = lambda path: (
            source_blob if path.endswith("job_letter.png") else pdf_blob
        )

        filename, content_type, storage_path = normalize_uploaded_document(
            bucket,
            self.application.application_id,
            DocumentType.JOB_LETTER,
            "photo.png",
            "image/png",
        )

        self.assertEqual(filename, "photo.pdf")
        self.assertEqual(content_type, "application/pdf")
        self.assertTrue(storage_path.endswith("/job_letter.pdf"))
        converted = pdf_blob.upload_from_string.call_args.args[0]
        self.assertTrue(converted.startswith(b"%PDF"))
        self.assertEqual(
            pdf_blob.upload_from_string.call_args.kwargs["content_type"],
            "application/pdf",
        )
        source_blob.delete.assert_called_once_with()

    def test_pdf_is_kept_without_reencoding(self):
        bucket = MagicMock()
        bucket.blob.return_value.download_as_bytes.return_value = b"%PDF-1.7\n"
        filename, content_type, storage_path = normalize_uploaded_document(
            bucket,
            self.application.application_id,
            DocumentType.PAYSLIP_01,
            "pay.PDF",
            "application/pdf",
        )

        self.assertEqual(filename, "pay.pdf")
        self.assertEqual(content_type, "application/pdf")
        self.assertTrue(storage_path.endswith("/payslip_01.pdf"))
        bucket.blob.return_value.download_as_bytes.assert_called_once_with()
        bucket.blob.return_value.upload_from_string.assert_not_called()
