import os
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from backend import application
from backend.main import app
from backend.models import DocumentType


class ApiTests(unittest.TestCase):
    def setUp(self):
        application._APPLICATIONS.clear()
        self.client = TestClient(app)

    def tearDown(self):
        application._APPLICATIONS.clear()

    def _create_application(self):
        response = self.client.post("/api/applications")
        self.assertEqual(response.status_code, 201)
        return response.json()

    def _process_all_documents(self, application_id):
        response = self.client.post(
            f"/api/applications/{application_id}/documents/start"
        )
        self.assertEqual(response.status_code, 200)

        for document_type in (
            DocumentType.JOB_LETTER,
            DocumentType.PAYSLIP_01,
            DocumentType.SALARY_ASSIGNMENT_FORM,
        ):
            received = self.client.post(
                f"/api/applications/{application_id}/documents/"
                f"{document_type.value}/received",
                json={
                    "filename": f"{document_type.value}.pdf",
                    "content_type": "application/pdf",
                },
            )
            self.assertEqual(received.status_code, 200)

            processing = self.client.post(
                f"/api/applications/{application_id}/documents/"
                f"{document_type.value}/processing"
            )
            self.assertEqual(processing.status_code, 200)

            processed = self.client.post(
                f"/api/applications/{application_id}/documents/"
                f"{document_type.value}/processed",
                json={"extracted_data": {"verified": True}},
            )
            self.assertEqual(processed.status_code, 200)

    def test_application_update_and_lookup(self):
        created = self._create_application()
        application_id = created["application_id"]

        updated = self.client.patch(
            f"/api/applications/{application_id}/sections/personal",
            json={
                "values": {
                    "first_name": "Alicia",
                    "last_name": "Brown",
                }
            },
        )
        self.assertEqual(updated.status_code, 200)

        fetched = self.client.get(f"/api/applications/{application_id}")
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.json()["personal"]["first_name"], "Alicia")

    def test_unknown_application_returns_404(self):
        response = self.client.get("/api/applications/APP-2099-NOTFOUND")
        self.assertEqual(response.status_code, 404)

    def test_obsolete_decision_endpoint_is_not_exposed(self):
        response = self.client.post("/api/decision", json={})
        self.assertEqual(response.status_code, 404)

    def test_full_fail_result_workflow_ends_in_received(self):
        created = self._create_application()
        application_id = created["application_id"]
        self._process_all_documents(application_id)

        consent = self.client.post(
            f"/api/applications/{application_id}/credit-consent",
            json={"consent": True},
        )
        self.assertEqual(consent.status_code, 200)

        credit = self.client.post(
            f"/api/applications/{application_id}/credit-check",
            json={"result": "FAIL"},
        )
        self.assertEqual(credit.status_code, 200)
        self.assertEqual(credit.json()["credit_bureau"]["result"], "FAIL")

        validation = self.client.post(
            f"/api/applications/{application_id}/validate"
        )
        self.assertEqual(validation.status_code, 200)
        self.assertEqual(validation.json()["status"], "READY_FOR_SUBMISSION")

        submitted = self.client.post(
            f"/api/applications/{application_id}/submit"
        )
        self.assertEqual(submitted.status_code, 200)
        self.assertEqual(submitted.json()["status"], "RECEIVED")
        self.assertNotIn("approved", submitted.text.lower())
        self.assertNotIn("declined", submitted.text.lower())

        fetched = self.client.get(f"/api/applications/{application_id}")
        self.assertEqual(fetched.json()["status"], "SUBMITTED")

    def test_signed_upload_uses_canonical_storage_path(self):
        created = self._create_application()
        application_id = created["application_id"]
        self.client.patch(
            f"/api/applications/{application_id}/sections/personal",
            json={
                "values": {
                    "first_name": "Alicia",
                    "last_name": "Brown",
                }
            },
        )

        blob = MagicMock()
        blob.generate_signed_url.return_value = "https://upload.example/signed"
        storage_client = MagicMock()
        storage_client.bucket.return_value.blob.return_value = blob

        with patch.dict(os.environ, {"UPLOAD_BUCKET": "loan-documents"}):
            with patch(
                "backend.main.storage.Client",
                return_value=storage_client,
            ):
                response = self.client.post(
                    f"/api/applications/{application_id}/documents/"
                    "job_letter/upload-url",
                    json={
                        "filename": "original.PDF",
                        "content_type": "application/pdf",
                    },
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["storage_path"],
            f"loan-applications/Alicia_Brown/{application_id}/job_letter.pdf",
        )


if __name__ == "__main__":
    unittest.main()
