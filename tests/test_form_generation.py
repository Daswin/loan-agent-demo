import unittest

from fastapi.testclient import TestClient

from backend import application
from backend.application import create_application, update_application_field
from backend.form_generation import generate_salary_assignment_form
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


if __name__ == "__main__":
    unittest.main()
