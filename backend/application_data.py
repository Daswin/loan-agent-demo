import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from .models import DocumentStatus, LoanApplication


SCHEMA = json.loads(
    (Path(__file__).with_name("application_schema.json")).read_text(
        encoding="utf-8"
    )
)
INFORMATION_SCHEMA = {
    key: value for key, value in SCHEMA.items() if key != "documents"
}

PROFILE_NAMES = {
    "marcus": ("Marcus", "Bell"),
    "dana": ("Dana", "Carter"),
    "james": ("James", "Foster"),
    "tanya": ("Tanya", "Reed"),
    "keith": ("Keith", "Shaw"),
}

PROFILE_SETTINGS = {
    "marcus": {"employment": "Salaried", "parish": "Kingston", "index": 1},
    "dana": {"employment": "Commissioned", "parish": "St. Andrew", "index": 2},
    "james": {"employment": "Self-employed", "parish": "St. James", "index": 3},
    "tanya": {"employment": "Salaried", "parish": "St. Catherine", "index": 4},
    "keith": {"employment": "Salaried", "parish": "Clarendon", "index": 5},
}

CONDITIONAL_PREFIXES = {
    "applicant.previous_address": "applicant.previous_address.applicable",
    "applicant.self_employment": "applicant.self_employment.applicable",
    "spouse": "spouse.applicable",
    "co_applicant": "co_applicant.applicable",
}

CORE_PATHS = {
    "applicant.identity.first_name",
    "applicant.identity.last_name",
    "applicant.identity.trn_tax_id",
    "applicant.contact.personal_email",
    "applicant.contact.mobile_phone",
    "applicant.current_address.address_line_1",
    "applicant.current_address.city_town",
    "applicant.current_address.parish_state",
    "applicant.employment.employment_status",
    "applicant.employment.employer_name",
    "applicant.income.gross_monthly_salary",
    "loan_request.product_type",
    "loan_request.requested_amount",
}

REQUIRED_INFORMATION_PATHS = [
    "applicant.identity.first_name",
    "applicant.identity.last_name",
    "applicant.identity.date_of_birth",
    "applicant.identity.trn_tax_id",
    "applicant.identity.primary_id.type",
    "applicant.identity.primary_id.number",
    "applicant.contact.personal_email",
    "applicant.contact.mobile_phone",
    "applicant.current_address.address_line_1",
    "applicant.current_address.city_town",
    "applicant.current_address.parish_state",
    "applicant.employment.employment_status",
    "applicant.employment.employer_name",
    "applicant.employment.job_title",
    "applicant.income.gross_monthly_salary",
    "applicant.income.net_monthly_salary",
    "applicant.banking.primary_bank",
    "loan_request.requested_amount",
    "loan_request.loan_purpose",
    "loan_request.requested_term_months",
]


def get_path(data: Any, path: str, default: Any = None) -> Any:
    current = data
    for part in path.split("."):
        try:
            current = current[int(part)] if isinstance(current, list) else current[part]
        except (KeyError, IndexError, TypeError, ValueError):
            return default
    return current


def set_path(data: Any, path: str, value: Any) -> None:
    parts = path.split(".")
    current = data
    for part in parts[:-1]:
        current = current[int(part)] if isinstance(current, list) else current[part]
    last = parts[-1]
    if isinstance(current, list):
        current[int(last)] = value
    else:
        current[last] = value


def _leaf_paths(value: Any, prefix: str = "") -> list[str]:
    if isinstance(value, dict):
        paths = []
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else key
            paths.extend(_leaf_paths(child, child_prefix))
        return paths
    if isinstance(value, list):
        paths = []
        for index, child in enumerate(value):
            paths.extend(_leaf_paths(child, f"{prefix}.{index}"))
        return paths
    return [prefix]


def required_field_paths(data: dict[str, Any]) -> list[str]:
    return list(REQUIRED_INFORMATION_PATHS)


def _demo_value(path: str, profile_id: str) -> Any:
    first_name, last_name = PROFILE_NAMES[profile_id]
    settings = PROFILE_SETTINGS[profile_id]
    index = settings["index"]
    key = path.split(".")[-1]
    schema_value = get_path(INFORMATION_SCHEMA, path)

    explicit = {
        "applicant.identity.first_name": first_name,
        "applicant.identity.last_name": last_name,
        "applicant.identity.title": "Ms." if profile_id in {"dana", "tanya"} else "Mr.",
        "applicant.identity.gender": "Female" if profile_id in {"dana", "tanya"} else "Male",
        "applicant.identity.nationality": "Jamaican",
        "applicant.identity.citizenship": "Jamaican",
        "applicant.identity.country_of_residence": "Jamaica",
        "applicant.identity.trn_tax_id": f"10{index}-20{index}-30{index}",
        "applicant.contact.personal_email": f"{first_name.lower()}.{last_name.lower()}@example.com",
        "applicant.contact.mobile_phone": f"876-555-01{index:02d}",
        "applicant.current_address.address_line_1": f"{10 + index} Hope Road",
        "applicant.current_address.city_town": "Kingston" if index != 3 else "Montego Bay",
        "applicant.current_address.parish_state": settings["parish"],
        "applicant.current_address.country": "Jamaica",
        "applicant.employment.employment_status": settings["employment"],
        "applicant.employment.employment_type": "Full-time",
        "applicant.employment.employer_name": f"Caribbean Services {index} Ltd.",
        "applicant.employment.job_title": ["Analyst", "Sales Manager", "Director", "Nurse", "Engineer"][index - 1],
        "applicant.income.gross_monthly_salary": 280000 + index * 35000,
        "applicant.income.net_monthly_salary": 215000 + index * 28000,
        "applicant.income.pay_frequency": "Monthly",
        "applicant.banking.primary_bank": "Meridian Private Bank",
        "loan_request.product_type": "Digital Personal Loan",
        "loan_request.loan_purpose": ["Home improvement", "Education", "Business equipment", "Medical expenses", "Debt consolidation"][index - 1],
        "loan_request.preferred_repayment_frequency": "Monthly",
        "loan_request.requested_term_months": 36 + index * 6,
        "applicant.identity.primary_id.type": "Driver's Licence",
        "applicant.identity.primary_id.number": f"DL-{index}02468{index}",
        "applicant.previous_address.applicable": profile_id == "dana",
        "applicant.self_employment.applicable": settings["employment"] == "Self-employed",
        "spouse.applicable": profile_id == "tanya",
        "co_applicant.applicable": profile_id == "keith",
        "loan_request.existing_debt_to_be_consolidated": profile_id == "keith",
        "emergency_contact.full_name": f"Alex {last_name}",
        "emergency_contact.mobile_phone": f"876-555-11{index:02d}",
    }
    if path in explicit:
        return explicit[path]
    if isinstance(schema_value, bool):
        return False
    if isinstance(schema_value, (int, float)):
        if key.startswith("number_of"):
            return index % 3
        if "year" in key or "month" in key:
            return index + 1
        if "percentage" in key:
            return 100
        return 5000 * (index + 1)
    if "date" in key:
        return f"202{index}-0{(index % 9) + 1}-15"
    if "email" in key:
        return f"{key.replace('_email', '')}.{index}@example.com"
    if "phone" in key:
        return f"876-555-{index}{len(path) % 1000:03d}"
    if "country" in key:
        return "Jamaica"
    if "parish" in key:
        return settings["parish"]
    if "name" in key:
        return f"{first_name} {last_name}"
    if "address" in key:
        return f"{20 + index} Constant Spring Road"
    if key in {"city_town", "place_of_birth"}:
        return "Kingston"
    return f"Demo {key.replace('_', ' ')} {index}"


def create_profile_data(
    profile_id: str,
    requested_amount: float | None = None,
) -> tuple[dict[str, Any], list[str]]:
    if profile_id not in PROFILE_NAMES:
        raise ValueError(f"Unknown customer profile '{profile_id}'.")

    data = copy.deepcopy(INFORMATION_SCHEMA)
    settings = PROFILE_SETTINGS[profile_id]
    set_path(data, "applicant.previous_address.applicable", profile_id == "dana")
    set_path(data, "applicant.self_employment.applicable", settings["employment"] == "Self-employed")
    set_path(data, "spouse.applicable", profile_id == "tanya")
    set_path(data, "co_applicant.applicable", profile_id == "keith")
    set_path(data, "loan_request.existing_debt_to_be_consolidated", profile_id == "keith")

    paths = required_field_paths(data)
    ranked = sorted(
        paths,
        key=lambda path: hashlib.sha256(f"{profile_id}:{path}".encode()).hexdigest(),
    )
    target = 13
    applicable_paths = set(paths)
    always_provided = {
        "applicant.identity.first_name",
        "applicant.identity.last_name",
        "loan_request.requested_amount",
    }
    provided = always_provided & applicable_paths
    for path in ranked:
        if len(provided) >= target:
            break
        provided.add(path)

    for path in paths:
        if path in provided:
            set_path(data, path, _demo_value(path, profile_id))

    first_name, last_name = PROFILE_NAMES[profile_id]
    set_path(data, "applicant.identity.first_name", first_name)
    set_path(data, "applicant.identity.last_name", last_name)
    if requested_amount is not None:
        set_path(data, "loan_request.requested_amount", requested_amount)
    return data, sorted(provided & set(paths))


def field_label(path: str) -> str:
    section = path.split(".")[-2] if len(path.split(".")) > 1 else "application"
    field = path.split(".")[-1]
    if field.isdigit():
        field = path.split(".")[-2]
    return f"{field.replace('_', ' ').title()} ({section.replace('_', ' ')})"


def calculate_completion(application: LoanApplication) -> dict[str, Any]:
    required = required_field_paths(application.application_data) if application.application_data else []
    provided = set(application.provided_fields)
    completed_fields = sum(path in provided for path in required)
    information_percent = round(completed_fields / len(required) * 100) if required else 0

    required_documents = application.documents
    completed_documents = sum(
        document.status in {
            DocumentStatus.RECEIVED,
            DocumentStatus.PROCESSING,
            DocumentStatus.PROCESSED,
        }
        for document in required_documents
    )
    documents_percent = round(
        completed_documents / len(required_documents) * 100
    ) if required_documents else 0
    total_items = len(required) + len(required_documents)
    completed_items = completed_fields + completed_documents
    overall_percent = round(completed_items / total_items * 100) if total_items else 0
    missing = [path for path in required if path not in provided]
    return {
        "overall_percent": overall_percent,
        "information_percent": information_percent,
        "documents_percent": documents_percent,
        "fields_completed": completed_fields,
        "fields_required": len(required),
        "documents_completed": completed_documents,
        "documents_required": len(required_documents),
        "next_missing_field": missing[0] if missing else None,
        "next_missing_field_label": field_label(missing[0]) if missing else None,
        "missing_fields": missing,
    }


def refresh_completion(application: LoanApplication) -> None:
    application.completion = calculate_completion(application)


def update_application_field(
    application: LoanApplication,
    field_path: str,
    value: Any,
) -> None:
    required = set(required_field_paths(application.application_data))
    if field_path not in required:
        raise ValueError(f"'{field_path}' is not an applicable application field.")
    set_path(application.application_data, field_path, value)
    if field_path not in application.provided_fields:
        application.provided_fields.append(field_path)
        application.provided_fields.sort()
    refresh_completion(application)
