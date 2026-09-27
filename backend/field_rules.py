import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Callable


FIELD_QUESTIONS = {
    "applicant.identity.first_name": "What is your first name?",
    "applicant.identity.last_name": "What is your last name?",
    "applicant.identity.date_of_birth": (
        "What is your date of birth using DD/MM/YYYY?"
    ),
    "applicant.identity.trn_tax_id": "What is your nine-digit TRN?",
    "applicant.identity.primary_id.type": (
        "Which photo ID will you use: Driver's Licence, Passport, or Voter's ID?"
    ),
    "applicant.identity.primary_id.number": (
        "What is the identification number shown on that photo ID?"
    ),
    "applicant.contact.personal_email": (
        "What email address should we use to contact you?"
    ),
    "applicant.contact.mobile_phone": (
        "What is the best mobile phone number to reach you?"
    ),
    "applicant.current_address.address_line_1": (
        "What is the street address where you currently live?"
    ),
    "applicant.current_address.city_town": (
        "Which city or town do you currently live in?"
    ),
    "applicant.current_address.parish_state": (
        "Which parish or state do you currently live in?"
    ),
    "applicant.employment.employment_status": (
        "What is your employment status: Salaried, Self-employed, Commissioned, or Other?"
    ),
    "applicant.employment.employer_name": (
        "What is the name of your current employer?"
    ),
    "applicant.employment.job_title": "What is your current job title?",
    "applicant.income.gross_monthly_salary": (
        "What is your gross monthly salary before deductions, in Jamaican dollars?"
    ),
    "applicant.income.net_monthly_salary": (
        "What is your net monthly salary after deductions, in Jamaican dollars?"
    ),
    "applicant.banking.primary_bank": "Which bank do you primarily use?",
    "loan_request.requested_amount": (
        "How much would you like to borrow, in Jamaican dollars?"
    ),
    "loan_request.loan_purpose": (
        "What is the loan for: Home improvement, Education, Medical expenses, "
        "Debt consolidation, or Other?"
    ),
    "loan_request.requested_term_months": (
        "What loan term would you prefer, in months?"
    ),
}


FIELD_LABELS = {
    "applicant.identity.first_name": "First name",
    "applicant.identity.last_name": "Last name",
    "applicant.identity.date_of_birth": "Date of birth",
    "applicant.identity.trn_tax_id": "TRN",
    "applicant.identity.primary_id.type": "Photo ID type",
    "applicant.identity.primary_id.number": "Photo ID number",
    "applicant.contact.personal_email": "Personal email address",
    "applicant.contact.mobile_phone": "Mobile phone number",
    "applicant.current_address.address_line_1": "Current street address",
    "applicant.current_address.city_town": "Current city or town",
    "applicant.current_address.parish_state": "Current parish or state",
    "applicant.employment.employment_status": "Employment status",
    "applicant.employment.employer_name": "Employer name",
    "applicant.employment.job_title": "Job title",
    "applicant.income.gross_monthly_salary": "Gross monthly salary",
    "applicant.income.net_monthly_salary": "Net monthly salary",
    "applicant.banking.primary_bank": "Primary bank",
    "loan_request.requested_amount": "Requested loan amount",
    "loan_request.loan_purpose": "Loan purpose",
    "loan_request.requested_term_months": "Requested loan term",
}


def field_question(path: str) -> str:
    return FIELD_QUESTIONS.get(path, f"Please provide your {field_label(path).lower()}.")


def field_label(path: str) -> str:
    if path in FIELD_LABELS:
        return FIELD_LABELS[path]
    return path.split(".")[-1].replace("_", " ").title()


def _text(value: Any, label: str, minimum: int = 2, maximum: int = 120) -> str:
    if not isinstance(value, str):
        raise ValueError(f"Please enter {label} as text.")
    normalized = re.sub(r"\s+", " ", value).strip()
    if not minimum <= len(normalized) <= maximum:
        raise ValueError(
            f"Please enter {label} using between {minimum} and {maximum} characters."
        )
    return normalized


def _name(value: Any, label: str) -> str:
    normalized = _text(value, label, 2, 60)
    if not re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ' -]+", normalized):
        raise ValueError(
            f"Please enter a valid {label}; use letters, spaces, hyphens, or apostrophes only."
        )
    return normalized


def _date_of_birth(value: Any) -> str:
    normalized = _text(value, "date of birth", 8, 10)
    parsed = None
    for date_format in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            parsed = datetime.strptime(normalized, date_format).date()
            break
        except ValueError:
            continue
    if parsed is None or parsed >= date.today():
        raise ValueError("Please enter a valid past date using DD/MM/YYYY.")
    return parsed.isoformat()


def _trn(value: Any) -> str:
    normalized = str(value).strip()
    if not re.fullmatch(r"[0-9]{9}", normalized):
        raise ValueError("Your TRN must contain exactly 9 numbers, with no spaces or dashes.")
    return normalized


def _choice(value: Any, label: str, choices: tuple[str, ...]) -> str:
    normalized = _text(value, label, 2, 60)
    lookup = {choice.casefold(): choice for choice in choices}
    try:
        return lookup[normalized.casefold()]
    except KeyError as exc:
        options = ", ".join(choices[:-1]) + f", or {choices[-1]}"
        raise ValueError(f"Please choose {label} from: {options}.") from exc


def _id_number(value: Any) -> str:
    normalized = _text(value, "photo ID number", 4, 30)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 /-]*", normalized):
        raise ValueError(
            "Please enter the ID number using letters, numbers, spaces, slashes, or dashes only."
        )
    return normalized


def _email(value: Any) -> str:
    normalized = _text(value, "email address", 5, 254).lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", normalized):
        raise ValueError("Please enter a valid email address, such as name@example.com.")
    return normalized


def _phone(value: Any) -> str:
    normalized = _text(value, "mobile phone number", 7, 25)
    if not re.fullmatch(r"\+?[0-9() .-]+", normalized):
        raise ValueError(
            "Please enter a valid phone number using digits and common separators, "
            "with an optional + prefix."
        )
    digits = re.sub(r"\D", "", normalized)
    if not 7 <= len(digits) <= 15:
        raise ValueError("Please enter a phone number containing between 7 and 15 digits.")
    return f"+{digits}" if normalized.startswith("+") else digits


def _money(value: Any, label: str, allow_zero: bool = False) -> int | float:
    if isinstance(value, bool):
        raise ValueError(f"Please enter {label} as a number.")
    normalized = str(value).strip().replace(",", "")
    normalized = re.sub(r"^(?:J\$|JM\$|\$)\s*", "", normalized, flags=re.IGNORECASE)
    try:
        amount = Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError(f"Please enter {label} as a number, without words.") from exc
    if not amount.is_finite():
        raise ValueError(f"Please enter {label} as a valid numeric amount.")
    minimum_valid = amount >= 0 if allow_zero else amount > 0
    if not minimum_valid:
        qualifier = "zero or more" if allow_zero else "greater than zero"
        raise ValueError(f"Please enter {label} as an amount {qualifier}.")
    if amount.as_tuple().exponent < -2:
        raise ValueError(f"Please enter {label} with no more than two decimal places.")
    return int(amount) if amount == amount.to_integral() else float(amount)


def _term(value: Any) -> int:
    normalized = str(value).strip()
    if not re.fullmatch(r"[0-9]+", normalized):
        raise ValueError("Please enter the preferred loan term as a whole number of months.")
    months = int(normalized)
    if not 1 <= months <= 360:
        raise ValueError("Please enter a loan term between 1 and 360 months.")
    return months


VALIDATORS: dict[str, Callable[[Any], Any]] = {
    "applicant.identity.first_name": lambda value: _name(value, "first name"),
    "applicant.identity.last_name": lambda value: _name(value, "last name"),
    "applicant.identity.date_of_birth": _date_of_birth,
    "applicant.identity.trn_tax_id": _trn,
    "applicant.identity.primary_id.type": lambda value: _choice(
        value, "a photo ID type", ("Driver's Licence", "Passport", "Voter's ID")
    ),
    "applicant.identity.primary_id.number": _id_number,
    "applicant.contact.personal_email": _email,
    "applicant.contact.mobile_phone": _phone,
    "applicant.current_address.address_line_1": lambda value: _text(
        value, "your current street address", 5, 120
    ),
    "applicant.current_address.city_town": lambda value: _text(
        value, "your current city or town", 2, 60
    ),
    "applicant.current_address.parish_state": lambda value: _text(
        value, "your current parish or state", 2, 60
    ),
    "applicant.employment.employment_status": lambda value: _choice(
        value, "an employment status", ("Salaried", "Self-employed", "Commissioned", "Other")
    ),
    "applicant.employment.employer_name": lambda value: _text(
        value, "your employer's name", 2, 100
    ),
    "applicant.employment.job_title": lambda value: _text(
        value, "your job title", 2, 80
    ),
    "applicant.income.gross_monthly_salary": lambda value: _money(
        value, "your gross monthly salary"
    ),
    "applicant.income.net_monthly_salary": lambda value: _money(
        value, "your net monthly salary", allow_zero=True
    ),
    "applicant.banking.primary_bank": lambda value: _text(
        value, "your primary bank's name", 2, 100
    ),
    "loan_request.requested_amount": lambda value: _money(
        value, "the requested loan amount"
    ),
    "loan_request.loan_purpose": lambda value: _choice(
        value,
        "a loan purpose",
        ("Home improvement", "Education", "Medical expenses", "Debt consolidation", "Other"),
    ),
    "loan_request.requested_term_months": _term,
}


def validate_field_value(path: str, value: Any) -> Any:
    validator = VALIDATORS.get(path)
    if validator is None:
        raise ValueError(f"No validation rule is configured for '{path}'.")
    return validator(value)
