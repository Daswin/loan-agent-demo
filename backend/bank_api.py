from typing import Any, Callable, Dict, Optional
from uuid import uuid4

from .application import get_application, set_application_status, utc_now
from .models import ApplicationStatus, LoanApplication


BankTransport = Callable[[Dict[str, Any]], Dict[str, Any]]


def build_bank_payload(application: LoanApplication) -> Dict[str, Any]:
    """Build the final package sent to the simulated bank."""
    return application.model_dump(
        mode="json",
        exclude={
            "bank_submission_reference",
            "submitted_at",
            "submission_error",
        },
    )


def _simulated_bank_transport(
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """Acknowledge receipt without approving or declining the application."""
    del payload
    return {
        "status": "RECEIVED",
        "reference": f"BANK-{uuid4().hex[:10].upper()}",
    }


def submit_application(
    application_id: str,
    transport: Optional[BankTransport] = None,
) -> Dict[str, Any]:
    """Submit a ready package and record receipt or submission failure."""
    application = get_application(application_id)

    if application.status != ApplicationStatus.READY_FOR_SUBMISSION:
        raise ValueError(
            "Application must be READY_FOR_SUBMISSION before submission."
        )

    bank_transport = transport or _simulated_bank_transport

    try:
        response = bank_transport(build_bank_payload(application))
        if response.get("status") != "RECEIVED":
            raise ValueError("Bank response did not acknowledge receipt.")

        reference = response.get("reference")
        if not reference:
            raise ValueError("Bank response did not include a reference.")

        submitted_at = utc_now()
        application.bank_submission_reference = str(reference)
        application.submitted_at = submitted_at
        application.submission_error = None
        set_application_status(
            application_id,
            ApplicationStatus.SUBMITTED,
        )
        return {
            "status": "RECEIVED",
            "reference": application.bank_submission_reference,
            "submitted_at": submitted_at.isoformat(),
        }
    except Exception as exc:
        application.submission_error = str(exc)
        set_application_status(
            application_id,
            ApplicationStatus.SUBMISSION_FAILED,
        )
        raise
