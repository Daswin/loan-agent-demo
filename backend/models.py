from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp for model defaults."""
    return datetime.now(timezone.utc)


class ApplicationStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    DOCUMENTS_REQUIRED = "DOCUMENTS_REQUIRED"
    DOCUMENTS_PROCESSING = "DOCUMENTS_PROCESSING"
    VALIDATION_REQUIRED = "VALIDATION_REQUIRED"
    READY_FOR_SUBMISSION = "READY_FOR_SUBMISSION"
    SUBMITTED = "SUBMITTED"
    SUBMISSION_FAILED = "SUBMISSION_FAILED"


class DocumentType(str, Enum):
    GOVERNMENT_PHOTO_ID = "government_photo_id"
    TRN_DOCUMENT = "trn_document"
    PROOF_OF_ADDRESS = "proof_of_address"
    JOB_LETTER = "job_letter"
    PAYSLIP_01 = "payslip_01"
    PAYSLIP_02 = "payslip_02"
    PAYSLIP_03 = "payslip_03"
    SALARY_ASSIGNMENT_FORM = "salary_assignment_form"
    PRO_FORMA_INVOICE = "pro_forma_invoice"
    PROOF_OF_LIABILITIES = "proof_of_liabilities"
    CREDIT_BUREAU_REPORT = "credit_bureau_report"
    BUSINESS_REGISTRATION = "business_registration"
    ANNUAL_RETURN = "annual_return"
    TAX_RETURN = "tax_return"
    FINANCIAL_STATEMENTS = "financial_statements"
    BUSINESS_BANK_STATEMENTS = "business_bank_statements"


class DocumentStatus(str, Enum):
    REQUIRED = "REQUIRED"
    RECEIVED = "RECEIVED"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class CreditResult(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class PersonalInformation(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    marital_status: Optional[str] = None
    nationality: Optional[str] = None
    id_type: Optional[str] = None
    id_number: Optional[str] = None


class ContactInformation(BaseModel):
    email: Optional[str] = None
    mobile_phone: Optional[str] = None
    alternate_phone: Optional[str] = None


class AddressInformation(BaseModel):
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city_town: Optional[str] = None
    parish_state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    years_at_address: Optional[float] = None


class PhysicianInformation(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None


class EmploymentInformation(BaseModel):
    employer_name: Optional[str] = None
    employer_address: Optional[str] = None
    employer_phone: Optional[str] = None
    job_title: Optional[str] = None
    employment_type: Optional[str] = None
    employment_start_date: Optional[str] = None
    years_employed: Optional[float] = None


class IncomeInformation(BaseModel):
    gross_monthly_salary: Optional[float] = None
    net_monthly_salary: Optional[float] = None
    pay_frequency: Optional[str] = None
    other_monthly_income: Optional[float] = None
    other_income_description: Optional[str] = None


class LoanInformation(BaseModel):
    requested_amount: Optional[float] = None
    loan_purpose: Optional[str] = None
    requested_term: Optional[int] = None
    preferred_payment_frequency: Optional[str] = None


class BankingInformation(BaseModel):
    bank_name: Optional[str] = None
    account_type: Optional[str] = None
    account_number: Optional[str] = None


class EmergencyContact(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    relationship: Optional[str] = None
    phone: Optional[str] = None


class CreditBureauResult(BaseModel):
    consent: bool = False
    result: Optional[CreditResult] = None
    reference: Optional[str] = None
    checked_at: Optional[datetime] = None


class DocumentRecord(BaseModel):
    document_type: DocumentType
    status: DocumentStatus = DocumentStatus.REQUIRED
    filename: Optional[str] = None
    storage_path: Optional[str] = None
    content_type: Optional[str] = None
    extracted_data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    received_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    upload_required: bool = True


class LoanApplication(BaseModel):
    application_id: str
    status: ApplicationStatus = ApplicationStatus.IN_PROGRESS
    profile_id: Optional[str] = None
    application_data: Dict[str, Any] = Field(default_factory=dict)
    provided_fields: List[str] = Field(default_factory=list)
    completion: Dict[str, Any] = Field(default_factory=dict)

    personal: PersonalInformation = Field(
        default_factory=PersonalInformation
    )
    contact: ContactInformation = Field(
        default_factory=ContactInformation
    )
    address: AddressInformation = Field(
        default_factory=AddressInformation
    )
    physician: PhysicianInformation = Field(
        default_factory=PhysicianInformation
    )
    employment: EmploymentInformation = Field(
        default_factory=EmploymentInformation
    )
    income: IncomeInformation = Field(
        default_factory=IncomeInformation
    )
    loan: LoanInformation = Field(
        default_factory=LoanInformation
    )
    banking: BankingInformation = Field(
        default_factory=BankingInformation
    )
    emergency_contact: EmergencyContact = Field(
        default_factory=EmergencyContact
    )

    credit_bureau: CreditBureauResult = Field(
        default_factory=CreditBureauResult
    )

    documents: List[DocumentRecord] = Field(
        default_factory=list
    )

    created_at: datetime = Field(
        default_factory=utc_now
    )
    updated_at: datetime = Field(
        default_factory=utc_now
    )

    bank_submission_reference: Optional[str] = None
    submitted_at: Optional[datetime] = None
    submission_error: Optional[str] = None
