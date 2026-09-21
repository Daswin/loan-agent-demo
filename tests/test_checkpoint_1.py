import unittest

from backend import application
from backend.application import (
    begin_document_collection,
    complete_validation,
    create_application,
    set_application_status,
)
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
        loan_application = create_application()
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

    def test_pass_and_fail_both_allow_completed_package_submission(self):
        for result in CreditResult:
            with self.subTest(result=result):
                application._APPLICATIONS.clear()
                loan_application = self._ready_application(result)
                receipt = submit_application(loan_application.application_id)

                self.assertEqual(receipt["status"], "RECEIVED")
                self.assertEqual(
                    loan_application.status,
                    ApplicationStatus.SUBMITTED,
                )
                self.assertNotIn("approved", str(receipt).lower())
                self.assertNotIn("declined", str(receipt).lower())

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
