from uuid import uuid4

from .application import get_application, save_application, utc_now
from .models import CreditResult, LoanApplication
from .models import DocumentStatus, DocumentType
from .application_data import refresh_completion


def record_credit_consent(
    application_id: str,
    consent: bool,
) -> LoanApplication:
    """Record the applicant's explicit credit-bureau consent choice."""
    application = get_application(application_id)
    application.credit_bureau.consent = consent

    if not consent:
        application.credit_bureau.result = None
        application.credit_bureau.reference = None
        application.credit_bureau.checked_at = None
        for document in application.documents:
            if document.document_type == DocumentType.CREDIT_BUREAU_REPORT:
                document.status = DocumentStatus.REQUIRED

    application.updated_at = utc_now()
    refresh_completion(application)
    save_application(application)
    return application


def run_simulated_credit_check(
    application_id: str,
    result: CreditResult,
) -> LoanApplication:
    """Record an operator-selected result; this is not a lending decision."""
    application = get_application(application_id)

    if not application.credit_bureau.consent:
        raise ValueError(
            "Customer consent is required before the credit bureau check."
        )

    now = utc_now()
    application.credit_bureau.result = result
    application.credit_bureau.reference = (
        f"CB-{uuid4().hex[:10].upper()}"
    )
    application.credit_bureau.checked_at = now
    for document in application.documents:
        if document.document_type == DocumentType.CREDIT_BUREAU_REPORT:
            document.status = DocumentStatus.PROCESSED
            document.processed_at = now
    application.updated_at = now
    refresh_completion(application)
    save_application(application)
    return application
