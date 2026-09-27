import unittest

from backend.application_data import REQUIRED_INFORMATION_PATHS
from backend.field_rules import FIELD_QUESTIONS, field_question, validate_field_value


class FieldRuleTests(unittest.TestCase):
    VALID_VALUES = {
        "applicant.identity.first_name": "Mary-Jane",
        "applicant.identity.last_name": "O'Connor",
        "applicant.identity.date_of_birth": "21/06/1988",
        "applicant.identity.trn_tax_id": "123456789",
        "applicant.identity.primary_id.type": "passport",
        "applicant.identity.primary_id.number": "AB-123456",
        "applicant.contact.personal_email": "Customer@Example.com",
        "applicant.contact.mobile_phone": "+1 (876) 555-0199",
        "applicant.current_address.address_line_1": "14 Hope Road",
        "applicant.current_address.city_town": "Kingston",
        "applicant.current_address.parish_state": "St. Andrew",
        "applicant.employment.employment_status": "self-employed",
        "applicant.employment.employer_name": "Island Services Limited",
        "applicant.employment.job_title": "Operations Manager",
        "applicant.income.gross_monthly_salary": "J$ 350,000.50",
        "applicant.income.net_monthly_salary": "275000",
        "applicant.banking.primary_bank": "Meridian Private Bank",
        "loan_request.requested_amount": "$2,500,000",
        "loan_request.loan_purpose": "education",
        "loan_request.requested_term_months": "60",
    }

    def test_every_required_field_has_a_specific_question_and_validator(self):
        self.assertEqual(set(FIELD_QUESTIONS), set(REQUIRED_INFORMATION_PATHS))
        for path in REQUIRED_INFORMATION_PATHS:
            with self.subTest(path=path):
                self.assertTrue(field_question(path).endswith("?"))
                validate_field_value(path, self.VALID_VALUES[path])

    def test_values_are_normalized_before_storage(self):
        self.assertEqual(
            validate_field_value("applicant.identity.date_of_birth", "21/06/1988"),
            "1988-06-21",
        )
        self.assertEqual(
            validate_field_value("applicant.contact.personal_email", "Customer@Example.com"),
            "customer@example.com",
        )
        self.assertEqual(
            validate_field_value("applicant.contact.mobile_phone", "+1 (876) 555-0199"),
            "+18765550199",
        )
        self.assertEqual(
            validate_field_value("loan_request.requested_amount", "J$ 2,500,000"),
            2_500_000,
        )

    def test_trn_requires_exactly_nine_digits(self):
        for invalid in ("12345678", "1234567890", "123-456-789", "abcdefghi"):
            with self.subTest(value=invalid), self.assertRaisesRegex(ValueError, "9 numbers"):
                validate_field_value("applicant.identity.trn_tax_id", invalid)

    def test_email_requires_a_valid_address_shape(self):
        for invalid in ("customer.example.com", "customer@", "@example.com"):
            with self.subTest(value=invalid), self.assertRaisesRegex(ValueError, "valid email"):
                validate_field_value("applicant.contact.personal_email", invalid)

    def test_categorical_fields_reject_unsupported_values(self):
        with self.assertRaisesRegex(ValueError, "Please choose"):
            validate_field_value("applicant.employment.employment_status", "Maybe")

    def test_loan_term_requires_a_reasonable_whole_number(self):
        for invalid in ("0", "12.5", "361", "twelve"):
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                validate_field_value("loan_request.requested_term_months", invalid)


if __name__ == "__main__":
    unittest.main()
