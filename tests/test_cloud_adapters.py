import os
import unittest
from unittest.mock import MagicMock, patch

from backend import application
from backend.application import begin_document_collection, create_application
from backend.document_processing import process_document_with_document_ai
from backend.documents import register_document_received
from backend.models import ApplicationStatus, DocumentStatus, DocumentType
from backend.repository import InMemoryApplicationRepository


class CloudAdapterTests(unittest.TestCase):
    def setUp(self):
        application._APPLICATIONS.clear()

    def tearDown(self):
        application._APPLICATIONS.clear()

    def test_in_memory_repository_implements_persistence_contract(self):
        store = {}
        repository = InMemoryApplicationRepository(store)
        loan_application = create_application()
        store.clear()

        repository.create(loan_application)
        loaded = repository.get(loan_application.application_id)

        self.assertIs(loaded, loan_application)
        self.assertEqual(repository.list(), [loan_application])

    def test_document_ai_adapter_persists_ocr_result(self):
        loan_application = create_application()
        begin_document_collection(loan_application.application_id)
        register_document_received(
            loan_application.application_id,
            DocumentType.JOB_LETTER,
            "letter.pdf",
            "application/pdf",
        )

        storage_client = MagicMock()
        storage_client.bucket.return_value.blob.return_value.download_as_bytes.return_value = b"pdf"
        document_ai_client = MagicMock()
        document_ai_client.processor_path.return_value = "processor/name"
        document_ai_client.process_document.return_value.document.text = "Employment verified"
        document_ai_client.process_document.return_value.document.pages = [object()]

        environment = {
            "GOOGLE_CLOUD_PROJECT": "test-project",
            "DOCAI_LOCATION": "us",
            "DOCAI_PROCESSOR_ID": "processor-123",
            "UPLOAD_BUCKET": "test-bucket",
        }
        with patch.dict(os.environ, environment, clear=False):
            with patch(
                "backend.document_processing.storage.Client",
                return_value=storage_client,
            ), patch(
                "backend.document_processing.documentai.DocumentProcessorServiceClient",
                return_value=document_ai_client,
            ):
                result = process_document_with_document_ai(
                    loan_application.application_id,
                    DocumentType.JOB_LETTER,
                )

        self.assertEqual(result["status"], DocumentStatus.PROCESSED.value)
        self.assertEqual(result["extracted_data"]["text"], "Employment verified")
        self.assertEqual(
            loan_application.status,
            ApplicationStatus.DOCUMENTS_PROCESSING,
        )

    def test_document_ai_configuration_is_required_before_state_change(self):
        loan_application = create_application()
        begin_document_collection(loan_application.application_id)
        document = register_document_received(
            loan_application.application_id,
            DocumentType.JOB_LETTER,
            "letter.pdf",
            "application/pdf",
        )

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "configuration missing"):
                process_document_with_document_ai(
                    loan_application.application_id,
                    DocumentType.JOB_LETTER,
                )

        self.assertEqual(document.status, DocumentStatus.RECEIVED)


if __name__ == "__main__":
    unittest.main()
