import unittest

from backend import application
from backend.application import (
    PackageValidationError,
    begin_document_collection,
    complete_validation,
    create_application,
    save_application,
    set_application_status,
    update_application_field,
)
from backend.application_data import _demo_value
from backend.bank_api import submit_application
from backend.credit_bureau import record_credit_consent, run_simulated_credit_check
from backend.documents import mark_document_processed, register_document_received
from backend.models import ApplicationStatus, CreditResult, DocumentType


class CheckpointOneTests(unittest.TestCase):
    def setUp(self):
        application._APPLICATIONS.clear()

    def tearDown(self):
        application._APPLICATIONS.clear()

    def _ready_application(self, credit_result=CreditResult.PASS):
        loan_application = create_application("marcus", 1_200_000)
        for field_path in list(loan_application.completion["missing_fields"]):
            update_application_field(
                loan_application.application_id,
                field_path,
                _demo_value(field_path, "marcus"),
            )
        begin_document_collection(loan_application.application_id)

        for document_type in [
            item.document_type for item in loan_application.documents
        ]:
            register_document_received(
                loan_application.application_id,
                document_type,
                f"{document_type.value}.pdf",
                "application/pdf",
            )
            mark_document_processed(
                loan_application.application_id,
                document_type,
                {"verified": True},
            )

        record_credit_consent(loan_application.application_id, True)
        run_simulated_credit_check(
            loan_application.application_id,
            credit_result,
        )
        complete_validation(loan_application.application_id)
        return loan_application

    def test_validation_rejects_missing_required_information(self):
        loan_application = create_application("marcus", 1_200_000)
        begin_document_collection(loan_application.application_id)
        for document_type in [item.document_type for item in loan_application.documents]:
            register_document_received(
                loan_application.application_id,
                document_type,
                f"{document_type.value}.pdf",
                "application/pdf",
            )
            mark_document_processed(
                loan_application.application_id,
                document_type,
                {"verified": True},
            )
        record_credit_consent(loan_application.application_id, True)
        run_simulated_credit_check(loan_application.application_id, CreditResult.PASS)

        with self.assertRaises(PackageValidationError) as context:
            complete_validation(loan_application.application_id)

        self.assertEqual(loan_application.status, ApplicationStatus.VALIDATION_REQUIRED)
        self.assertGreater(len(context.exception.missing_items), 0)

    def test_submission_rechecks_package_after_successful_validation(self):
        loan_application = self._ready_application()
        removed_field = loan_application.provided_fields.pop()
        save_application(loan_application)

        with self.assertRaises(PackageValidationError) as context:
            submit_application(loan_application.application_id)

        self.assertIn(
            removed_field,
            loan_application.completion.get("missing_fields", [])
            or [removed_field],
        )
        self.assertEqual(loan_application.status, ApplicationStatus.READY_FOR_SUBMISSION)

    def test_new_application_has_required_document_checklist(self):
        loan_application = create_application()
        self.assertEqual(loan_application.status, ApplicationStatus.IN_PROGRESS)
        self.assertEqual(
            {item.document_type for item in loan_application.documents},
            {
                DocumentType.JOB_LETTER,
                DocumentType.PAYSLIP_01,
                DocumentType.SALARY_ASSIGNMENT_FORM,
            },
        )

    def test_illegal_status_jump_is_rejected(self):
        loan_application = create_application()
        with self.assertRaisesRegex(ValueError, "Invalid application status"):
            set_application_status(
                loan_application.application_id,
                ApplicationStatus.SUBMITTED,
            )

    def test_credit_check_requires_consent(self):
        loan_application = create_application()
        with self.assertRaisesRegex(ValueError, "consent"):
            run_simulated_credit_check(
                loan_application.application_id,
                CreditResult.PASS,
            )

    def test_revoking_consent_clears_existing_credit_result(self):
        loan_application = create_application()
        record_credit_consent(loan_application.application_id, True)
        run_simulated_credit_check(
            loan_application.application_id,
            CreditResult.PASS,
        )

        record_credit_consent(loan_application.application_id, False)

        self.assertFalse(loan_application.credit_bureau.consent)
        self.assertIsNone(loan_application.credit_bureau.result)
        self.assertIsNone(loan_application.credit_bureau.reference)
        self.assertIsNone(loan_application.credit_bureau.checked_at)

    def test_pass_allows_completed_package_submission(self):
        loan_application = self._ready_application(CreditResult.PASS)
        receipt = submit_application(loan_application.application_id)

        self.assertEqual(receipt["status"], "RECEIVED")
        self.assertEqual(loan_application.status, ApplicationStatus.SUBMITTED)
        self.assertNotIn("approved", str(receipt).lower())
        self.assertNotIn("declined", str(receipt).lower())

    def test_fail_blocks_validation_and_submission_without_declining(self):
        loan_application = create_application("marcus", 1_200_000)
        for field_path in list(loan_application.completion["missing_fields"]):
            update_application_field(
                loan_application.application_id,
                field_path,
                _demo_value(field_path, "marcus"),
            )
        begin_document_collection(loan_application.application_id)
        for document_type in [item.document_type for item in loan_application.documents]:
            register_document_received(
                loan_application.application_id,
                document_type,
                f"{document_type.value}.pdf",
                "application/pdf",
            )
            mark_document_processed(
                loan_application.application_id,
                document_type,
                {"verified": True},
            )
        record_credit_consent(loan_application.application_id, True)
        run_simulated_credit_check(loan_application.application_id, CreditResult.FAIL)

        with self.assertRaisesRegex(PackageValidationError, "not complete"):
            complete_validation(loan_application.application_id)
        self.assertEqual(loan_application.status, ApplicationStatus.VALIDATION_REQUIRED)

        loan_application.status = ApplicationStatus.READY_FOR_SUBMISSION
        save_application(loan_application)
        with self.assertRaisesRegex(PackageValidationError, "not complete"):
            submit_application(loan_application.application_id)
        self.assertEqual(loan_application.status, ApplicationStatus.READY_FOR_SUBMISSION)

    def test_submission_failure_is_recorded(self):
        loan_application = self._ready_application()

        def failing_transport(payload):
            del payload
            raise RuntimeError("Simulated bank outage")

        with self.assertRaisesRegex(RuntimeError, "bank outage"):
            submit_application(
                loan_application.application_id,
                transport=failing_transport,
            )

        self.assertEqual(
            loan_application.status,
            ApplicationStatus.SUBMISSION_FAILED,
        )
        self.assertEqual(
            loan_application.submission_error,
            "Simulated bank outage",
        )


if __name__ == "__main__":
    unittest.main()
