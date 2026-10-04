import unittest
from math import isclose

from fastapi.testclient import TestClient

from backend import application
from backend.application import create_application, update_application_field
from backend.form_generation import _monthly_payment, generate_salary_assignment_form
from backend.main import app


class SalaryAssignmentFormTests(unittest.TestCase):
    def setUp(self):
        application._APPLICATIONS.clear()
        self.client = TestClient(app)

    def tearDown(self):
        application._APPLICATIONS.clear()

    def test_form_uses_prefilled_employee_name(self):
        loan_application = create_application("marcus", 1_200_000)
        document = generate_salary_assignment_form(loan_application)
        self.assertIn("Marcus Bell", document)
        self.assertIn(loan_application.application_id, document)
        self.assertIn("Print / Save as PDF", document)

    def test_form_uses_name_confirmed_during_conversation(self):
        loan_application = create_application("marcus", 1_200_000)
        update_application_field(
            loan_application.application_id,
            "applicant.identity.first_name",
            "Marcia",
        )
        update_application_field(
            loan_application.application_id,
            "applicant.identity.last_name",
            "Brown",
        )
        document = generate_salary_assignment_form(loan_application)
        self.assertIn("Marcia Brown", document)
        self.assertNotIn("Marcus Bell", document)

    def test_download_endpoint_returns_attachment(self):
        loan_application = create_application("dana", 2_500_000)
        response = self.client.get(
            f"/api/applications/{loan_application.application_id}/documents/"
            "salary_assignment_form/template"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn(
            "attachment;",
            response.headers["content-disposition"],
        )
        self.assertIn("Dana Carter", response.text)

    def test_form_includes_bank_monthly_frequency_and_amortized_payment(self):
        loan_application = create_application("marcus", 1_200_000)
        update_application_field(
            loan_application.application_id,
            "applicant.banking.primary_bank",
            "Meridian Private Bank",
        )
        update_application_field(
            loan_application.application_id,
            "loan_request.requested_term_months",
            36,
        )
        loan_application = application.get_application(
            loan_application.application_id,
        )
        document = generate_salary_assignment_form(loan_application)
        expected = _monthly_payment(1_200_000, 36)
        self.assertTrue(isclose(expected, 44_597.9617, rel_tol=0.0001))
        self.assertIn("Meridian Private Bank", document)
        self.assertIn("Payroll frequency", document)
        self.assertIn("Monthly", document)
        self.assertIn("Monthly deduction amount", document)
        self.assertIn(f"J${expected:,.2f}", document)
        self.assertNotIn("Annual interest rate", document)
        self.assertIn('class="deduction-amount"', document)


if __name__ == "__main__":
    unittest.main()
