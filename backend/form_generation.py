from html import escape

from .application_data import get_path
from .models import LoanApplication


def _text(value, fallback: str = "") -> str:
    if value is None or value == "":
        return fallback
    return escape(str(value))


def salary_assignment_filename(application: LoanApplication) -> str:
    identity = get_path(application.application_data, "applicant.identity", {})
    name = "_".join(
        part for part in (
            identity.get("first_name", ""),
            identity.get("last_name", ""),
        ) if part
    ) or "Applicant"
    safe_name = "".join(
        character if character.isalnum() or character in "-_" else "_"
        for character in name
    )
    return f"salary_assignment_form_{safe_name}.html"


def generate_salary_assignment_form(application: LoanApplication) -> str:
    data = application.application_data
    first_name = get_path(data, "applicant.identity.first_name", "")
    last_name = get_path(data, "applicant.identity.last_name", "")
    employee_name = " ".join(
        part for part in (first_name, last_name) if part
    ).strip()
    if not employee_name:
        employee_name = " ".join(
            part for part in (
                application.personal.first_name,
                application.personal.last_name,
            ) if part
        ).strip()
    if not employee_name:
        raise ValueError(
            "The applicant's name is required before generating this form."
        )

    employer = get_path(data, "applicant.employment.employer_name", "")
    requested_amount = get_path(data, "loan_request.requested_amount", "")
    bank = get_path(data, "applicant.banking.primary_bank", "Meridian Private Bank")

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Salary Deduction / Assignment Form</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: #eef1f5; color: #15233a; font: 15px/1.5 Arial, sans-serif; }}
    .toolbar {{ max-width: 850px; margin: 20px auto 0; text-align: right; }}
    .toolbar button {{ padding: 10px 18px; border: 0; background: #173a64; color: white; cursor: pointer; }}
    .page {{ width: 850px; min-height: 1050px; margin: 12px auto 30px; padding: 58px 64px; background: white; box-shadow: 0 10px 35px #aeb6c2; }}
    .rule {{ height: 5px; margin-bottom: 28px; background: #d4af37; }}
    h1 {{ margin: 0; color: #173a64; font-family: Georgia, serif; font-size: 25px; }}
    .subtitle {{ margin: 5px 0 28px; color: #66758a; }}
    .reference {{ float: right; font-size: 12px; color: #66758a; }}
    .field-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 19px 32px; margin: 28px 0; }}
    .field {{ border-bottom: 1px solid #53657a; min-height: 48px; }}
    .field span {{ display: block; color: #66758a; font-size: 11px; text-transform: uppercase; letter-spacing: .08em; }}
    .field strong {{ display: block; padding-top: 7px; font-weight: 600; }}
    .authorization {{ margin: 30px 0; padding: 20px; border: 1px solid #d8dee6; background: #f8fafc; }}
    .blank {{ display: inline-block; min-width: 180px; border-bottom: 1px solid #29384d; }}
    .signatures {{ display: grid; grid-template-columns: 1fr 1fr; gap: 45px; margin-top: 70px; }}
    .signature {{ padding-top: 8px; border-top: 1px solid #29384d; color: #66758a; font-size: 12px; }}
    .footer {{ margin-top: 65px; padding-top: 16px; border-top: 1px solid #d8dee6; color: #66758a; font-size: 11px; }}
    @media print {{ body {{ background: white; }} .toolbar {{ display: none; }} .page {{ width: auto; min-height: auto; margin: 0; box-shadow: none; }} }}
  </style>
</head>
<body>
  <div class="toolbar"><button onclick="window.print()">Print / Save as PDF</button></div>
  <main class="page">
    <div class="rule"></div>
    <span class="reference">Application {_text(application.application_id)}</span>
    <h1>Salary Deduction / Assignment Authorization</h1>
    <p class="subtitle">Complete, sign, and return this form with the loan application package.</p>

    <div class="field-grid">
      <div class="field"><span>Employee name</span><strong>{_text(employee_name)}</strong></div>
      <div class="field"><span>Employer</span><strong>{_text(employer, "To be completed")}</strong></div>
      <div class="field"><span>Employee number</span><strong>&nbsp;</strong></div>
      <div class="field"><span>Requested loan amount</span><strong>{_text(requested_amount)}</strong></div>
      <div class="field"><span>Financial institution</span><strong>{_text(bank)}</strong></div>
      <div class="field"><span>Payroll frequency</span><strong>&nbsp;</strong></div>
    </div>

    <section class="authorization">
      <p>I, <strong>{_text(employee_name)}</strong>, authorize my employer to deduct
      <span class="blank">&nbsp;</span> from my salary each pay period and remit that amount
      to <strong>{_text(bank)}</strong> toward my loan obligation.</p>
      <p>This authorization will remain in effect until the obligation has been satisfied
      or written instructions to amend or end it have been accepted by the employer and
      financial institution, subject to the applicable agreement.</p>
      <p>Deduction commencement date: <span class="blank">&nbsp;</span></p>
    </section>

    <div class="signatures">
      <div class="signature">Employee signature</div>
      <div class="signature">Date</div>
      <div class="signature">Authorized employer representative</div>
      <div class="signature">Date</div>
    </div>

    <p class="footer">This generated document is a prototype form and does not constitute loan approval or a lending decision.</p>
  </main>
</body>
</html>"""
