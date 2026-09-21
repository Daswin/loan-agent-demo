import unittest
from datetime import timedelta
from unittest.mock import patch

from backend.application import (
    begin_document_collection,
    create_application,
    is_application_inactive,
    reset_application,
    utc_now,
    update_application_field,
)
from backend.application_data import PROFILE_NAMES
from backend.documents import register_document_received
from backend.models import DocumentType


class ApplicationCompletionTests(unittest.TestCase):
    def test_demo_profiles_begin_with_13_of_20_fields_complete(self):
        profiles = [create_application(profile_id) for profile_id in PROFILE_NAMES]
        for application in profiles:
            with self.subTest(profile=application.profile_id):
                self.assertEqual(application.completion["fields_completed"], 13)
                self.assertEqual(application.completion["fields_required"], 20)
                self.assertEqual(application.completion["information_percent"], 65)
                self.assertTrue(application.completion["next_missing_field"])

        completed_sets = {
            tuple(application.provided_fields) for application in profiles
        }
        self.assertEqual(len(completed_sets), len(PROFILE_NAMES))

    def test_one_field_update_advances_completion(self):
        application = create_application("marcus")
        field_path = application.completion["next_missing_field"]
        completed_before = application.completion["fields_completed"]

        updated = update_application_field(
            application.application_id,
            field_path,
            "Applicant confirmed value",
        )

        self.assertEqual(
            updated.completion["fields_completed"],
            completed_before + 1,
        )
        self.assertIn(field_path, updated.provided_fields)

    def test_received_document_advances_overall_completion(self):
        application = create_application("marcus")
        begin_document_collection(application.application_id)
        overall_before = application.completion["overall_percent"]

        register_document_received(
            application.application_id,
            DocumentType.JOB_LETTER,
            "job_letter.pdf",
            "application/pdf",
        )

        self.assertEqual(application.completion["documents_completed"], 1)
        self.assertGreater(
            application.completion["overall_percent"],
            overall_before,
        )

    def test_document_mutation_persists_when_repository_returns_copies(self):
        class CopyingRepository:
            def __init__(self):
                self.items = {}

            def create(self, item):
                self.items[item.application_id] = item.model_copy(deep=True)

            def get(self, application_id):
                item = self.items.get(application_id)
                return item.model_copy(deep=True) if item else None

            def save(self, item):
                self.items[item.application_id] = item.model_copy(deep=True)

            def list(self):
                return [item.model_copy(deep=True) for item in self.items.values()]

        repository = CopyingRepository()
        with patch("backend.application._REPOSITORY", repository):
            application = create_application("marcus")
            begin_document_collection(application.application_id)
            register_document_received(
                application.application_id,
                DocumentType.JOB_LETTER,
                "job_letter.pdf",
                "application/pdf",
            )
            saved = repository.get(application.application_id)

        self.assertEqual(saved.documents[0].status.value, "RECEIVED")
        self.assertEqual(saved.completion["documents_completed"], 1)

    def test_demo_document_checklist_contains_three_documents(self):
        application = create_application("marcus", 2_000_000)
        self.assertEqual(
            {item.document_type for item in application.documents},
            {
                DocumentType.JOB_LETTER,
                DocumentType.PAYSLIP_01,
                DocumentType.SALARY_ASSIGNMENT_FORM,
            },
        )

    def test_reset_restores_original_profile_and_document_state(self):
        application = create_application("marcus", 2_000_000)
        original_fields = list(application.provided_fields)
        missing_field = application.completion["next_missing_field"]
        update_application_field(
            application.application_id,
            missing_field,
            "Temporary answer",
        )
        begin_document_collection(application.application_id)
        register_document_received(
            application.application_id,
            DocumentType.JOB_LETTER,
            "job_letter.pdf",
            "application/pdf",
        )

        reset = reset_application(application.application_id)

        self.assertEqual(reset.status.value, "IN_PROGRESS")
        self.assertEqual(reset.provided_fields, original_fields)
        self.assertEqual(reset.completion["fields_completed"], 13)
        self.assertEqual(reset.completion["documents_completed"], 0)
        self.assertEqual(reset.loan.requested_amount, 2_000_000)
        self.assertTrue(all(item.status.value == "REQUIRED" for item in reset.documents))
        self.assertIsNotNone(reset.last_reset_at)

    def test_five_minute_inactivity_threshold(self):
        application = create_application("dana")
        now = utc_now()
        application.last_activity_at = now - timedelta(minutes=4, seconds=59)
        self.assertFalse(is_application_inactive(application, now=now))
        application.last_activity_at = now - timedelta(minutes=5)
        self.assertTrue(is_application_inactive(application, now=now))


if __name__ == "__main__":
    unittest.main()
