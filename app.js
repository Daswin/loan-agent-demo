const API_BASE = window.LOAN_API_BASE || window.location.origin;
const SESSION_KEY = "loan-agent-session-id";
const SESSION_ID = localStorage.getItem(SESSION_KEY) || crypto.randomUUID();

const CUSTOMER_PROFILES = {
  marcus: { firstName: "Marcus", lastName: "Bell", baseLoanAmount: 1200000 },
  dana: { firstName: "Dana", lastName: "Carter", baseLoanAmount: 2500000 },
  james: { firstName: "James", lastName: "Foster", baseLoanAmount: 3000000 },
  tanya: { firstName: "Tanya", lastName: "Reed", baseLoanAmount: 1800000 },
  keith: { firstName: "Keith", lastName: "Shaw", baseLoanAmount: 3500000 },
};

const query = new URLSearchParams(window.location.search);
const customerId = query.get("customer");
const selectedCustomer = CUSTOMER_PROFILES[customerId] || null;
const requestedLoanAmountValue = query.get("loanAmount");
const requestedLoanAmount = Number(requestedLoanAmountValue);
const selectedLoanAmount = requestedLoanAmountValue !== null
  && Number.isFinite(requestedLoanAmount)
  && requestedLoanAmount >= 0
  && requestedLoanAmount <= 5000000
  ? requestedLoanAmount
  : selectedCustomer?.baseLoanAmount;
const APPLICATION_KEY = selectedCustomer
  ? `loan-agent-application-id:v3:${customerId}`
  : "loan-agent-application-id";

const DOCUMENT_LABELS = {
  government_photo_id: "Valid National Photo Identification",
  trn_document: "Tax Registration Number (TRN)",
  proof_of_address: "Valid Proof of Address",
  job_letter: "Job Letter",
  payslip_01: "Payslip",
  payslip_02: "Payslip #2",
  payslip_03: "Payslip #3",
  salary_assignment_form: "Salary Deduction / Assignment Form",
  pro_forma_invoice: "Proforma Invoice / Quotation",
  proof_of_liabilities: "Proof of Liabilities",
  credit_bureau_report: "Credit Bureau Report",
  business_registration: "Business Registration",
  annual_return: "Annual Return",
  tax_return: "Tax Return",
  financial_statements: "Financial Statements",
  business_bank_statements: "Business Bank Statements",
};

const FIELD_QUICK_REPLIES = {
  "applicant.identity.primary_id.type": ["Driver's Licence", "Passport", "Voter's ID"],
  "applicant.employment.employment_status": ["Salaried", "Self-employed", "Commissioned", "Other"],
  "loan_request.loan_purpose": ["Home improvement", "Education", "Medical expenses", "Debt consolidation", "Other"],
};

const PROBLEM_OPTIONS = [
  "Problem: My documents are delayed",
  "Problem: My employer will not sign the salary assignment form",
  "Problem: I cannot upload a document",
  "Problem: Some application information is incorrect",
  "Problem: I have a question about credit consent",
];

let applicationId = localStorage.getItem(APPLICATION_KEY);
let applicationState = null;
localStorage.setItem(SESSION_KEY, SESSION_ID);

const byId = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const error = await response.json();
      message = error.detail || message;
    } catch (_) {
      // Preserve the status-based message for non-JSON errors.
    }
    const apiError = new Error(message);
    apiError.status = response.status;
    throw apiError;
  }

  return response.status === 204 ? null : response.json();
}

function setNotice(message, kind = "") {
  const notice = byId("notice");
  notice.textContent = message;
  notice.className = kind;
}

function appendMessage(sender, text) {
  const message = document.createElement("div");
  message.className = `message ${sender}`;
  message.textContent = text;
  const chatWindow = byId("chat-window");
  chatWindow.appendChild(message);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function showQuickReplies(options = []) {
  const container = byId("quick-replies");
  container.replaceChildren();
  options.forEach((option) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "quick-reply";
    button.textContent = option;
    button.addEventListener("click", () => sendMessage(option));
    container.appendChild(button);
  });
}

function inferReplyOptions(reply) {
  if (/\b(agree|agreement|consent)\b/i.test(reply)) {
    return ["Agree", "Disagree"];
  }
  if (/\bconfirm\b/i.test(reply)) {
    return ["Confirm", "Decline"];
  }
  if (/\b(do|does|did|is|are|can|could|would|will|have|has)\b[^?]*\?/i.test(reply)) {
    return ["Yes", "No"];
  }
  return [];
}

async function createApplication() {
  applicationState = await api("/api/applications", {
    method: "POST",
    body: JSON.stringify({
      profile_id: customerId,
      requested_amount: selectedLoanAmount,
    }),
  });
  applicationId = applicationState.application_id;
  localStorage.setItem(APPLICATION_KEY, applicationId);
  applicationState = await api(
    `/api/applications/${applicationId}/documents/start`,
    { method: "POST" },
  );
  renderApplication();
}

async function refreshApplication() {
  if (!applicationId) {
    await createApplication();
    return;
  }

  try {
    applicationState = await api(`/api/applications/${applicationId}`);
  } catch (error) {
    if (error.status !== 404) throw error;
    localStorage.removeItem(APPLICATION_KEY);
    applicationId = null;
    await createApplication();
    return;
  }
  renderApplication();
}

function renderApplication() {
  if (!applicationState) return;
  byId("application-id").textContent = applicationState.application_id;
  const applicantName = [
    applicationState.personal.first_name,
    applicationState.personal.last_name,
  ].filter(Boolean).join(" ");
  byId("customer-name").textContent = applicantName || "New applicant";
  byId("application-status").textContent = applicationState.status;
  const completion = applicationState.completion || {};
  const overall = completion.overall_percent || 0;
  byId("completion-value").textContent = `${overall}%`;
  byId("completion-bar").style.width = `${overall}%`;
  byId("completion-track").setAttribute("aria-valuenow", String(overall));
  byId("information-progress").textContent =
    `Information ${completion.information_percent || 0}%`;
  byId("documents-progress").textContent =
    `Documents ${completion.documents_percent || 0}%`;
  const fieldsRemaining = (completion.fields_required || 0)
    - (completion.fields_completed || 0);
  const documentsRemaining = (completion.documents_required || 0)
    - (completion.documents_completed || 0);
  byId("completion-guidance").textContent = fieldsRemaining > 0
    ? `${fieldsRemaining} information ${fieldsRemaining === 1 ? "item" : "items"} and ${documentsRemaining} ${documentsRemaining === 1 ? "document" : "documents"} remaining.`
    : documentsRemaining > 0
      ? `Your information is complete. Upload ${documentsRemaining} remaining ${documentsRemaining === 1 ? "document" : "documents"} to finish the package.`
      : "Your information and required documents are complete.";
  byId("consent-checkbox").checked = applicationState.credit_bureau.consent;
  const workflowComplete = ["SUBMITTED", "SUBMISSION_FAILED"].includes(
    applicationState.status,
  );
  byId("consent-checkbox").disabled = workflowComplete;
  byId("save-consent-btn").disabled = workflowComplete;
  byId("credit-pass-btn").disabled =
    !applicationState.credit_bureau.consent || workflowComplete;
  byId("credit-fail-btn").disabled =
    !applicationState.credit_bureau.consent || workflowComplete;
  byId("start-documents-btn").disabled =
    applicationState.status !== "IN_PROGRESS";
  byId("validate-btn").disabled =
    applicationState.status !== "VALIDATION_REQUIRED";
  byId("submit-btn").disabled =
    applicationState.status !== "READY_FOR_SUBMISSION";
  renderDocuments();
}

function renderDocuments() {
  const container = byId("document-list");
  container.replaceChildren();

  applicationState.documents.forEach((record) => {
    const item = document.createElement("div");
    item.className = "document";

    const head = document.createElement("div");
    head.className = "document-head";
    const label = document.createElement("strong");
    label.textContent = DOCUMENT_LABELS[record.document_type];
    const status = document.createElement("span");
    status.className = "badge";
    status.textContent = record.status;
    head.append(label, status);

    const controls = document.createElement("div");
    controls.className = "document-controls";
    if (!record.upload_required) {
      const systemNote = document.createElement("span");
      systemNote.className = "muted";
      systemNote.textContent = "Provided through the simulated credit bureau check.";
      controls.append(systemNote);
      item.append(head, controls);
      container.appendChild(item);
      return;
    }
    if (record.document_type === "salary_assignment_form") {
      const generate = document.createElement("button");
      generate.type = "button";
      generate.className = "secondary";
      generate.textContent = "Generate form";
      generate.addEventListener("click", downloadSalaryAssignmentForm);
      controls.append(generate);
    }
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".pdf,.png,.jpg,.jpeg";
    input.disabled = !["DOCUMENTS_REQUIRED", "DOCUMENTS_PROCESSING"].includes(
      applicationState.status,
    );
    const upload = document.createElement("button");
    upload.type = "button";
    upload.textContent = "Upload";
    upload.disabled = input.disabled;
    const feedback = document.createElement("span");
    feedback.className = "document-feedback";
    feedback.textContent = record.filename
      ? `${record.filename} — ${record.status}`
      : "No document uploaded yet.";
    upload.addEventListener("click", () => uploadDocument(
      record.document_type,
      input,
      upload,
      feedback,
    ));
    controls.append(input, upload);

    if (["RECEIVED", "PROCESSING"].includes(record.status)) {
      const process = document.createElement("button");
      process.type = "button";
      process.className = "warning";
      process.textContent = "Process document";
      process.title = "Run Document AI OCR";
      process.addEventListener("click", () => processDocument(record));
      controls.append(process);
    }

    item.append(head, controls, feedback);
    container.appendChild(item);
  });
}

async function downloadSalaryAssignmentForm() {
  setNotice("Preparing the salary assignment form…");
  try {
    const response = await fetch(
      `${API_BASE}/api/applications/${applicationId}/documents/salary_assignment_form/template`,
    );
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Unable to generate the form.");
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    const applicantName = [
      applicationState.personal.first_name,
      applicationState.personal.last_name,
    ].filter(Boolean).join("_") || "Applicant";
    link.href = url;
    link.download = `salary_assignment_form_${applicantName}.html`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    setNotice("Form downloaded. Open it to print, save as PDF, or sign it.", "success");
  } catch (error) {
    setNotice(error.message, "error");
  }
}

async function sendMessage(messageOverride = null) {
  const input = byId("msg-input");
  const message = typeof messageOverride === "string"
    ? messageOverride.trim()
    : input.value.trim();
  if (!message || !applicationId) return;

  showQuickReplies();
  appendMessage("user", message);
  input.value = "";
  byId("send-btn").disabled = true;

  try {
    const result = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({
        session_id: SESSION_ID,
        application_id: applicationId,
        message,
      }),
    });
    appendMessage("agent", result.reply || "Your application was updated.");
    await refreshApplication();
    const problemMentioned = /problem|issue|trouble|delay|cannot|can't|won't|will not|refus|help/i.test(message);
    const responseOptions = (result.quick_replies || []).length
      ? result.quick_replies
      : inferReplyOptions(result.reply || "");
    showQuickReplies(problemMentioned ? PROBLEM_OPTIONS : responseOptions);
  } catch (error) {
    appendMessage("agent", `Unable to continue: ${error.message}`);
  } finally {
    byId("send-btn").disabled = false;
  }
}

async function startDocumentCollection() {
  try {
    applicationState = await api(
      `/api/applications/${applicationId}/documents/start`,
      { method: "POST" },
    );
    renderApplication();
    setNotice("Document collection started.", "success");
  } catch (error) {
    setNotice(error.message, "error");
  }
}

async function uploadDocument(documentType, input, uploadButton, feedback) {
  const file = input.files[0];
  if (!file) {
    setNotice("Select a file before uploading.", "error");
    feedback.textContent = "Choose a file first.";
    feedback.className = "document-feedback error";
    return;
  }

  const contentType = file.type || "application/octet-stream";
  setNotice(`Uploading ${DOCUMENT_LABELS[documentType]}…`);
  uploadButton.disabled = true;
  uploadButton.textContent = "Uploading…";
  feedback.textContent = `Uploading ${file.name}…`;
  feedback.className = "document-feedback";

  try {
    const signed = await api(
      `/api/applications/${applicationId}/documents/${documentType}/upload-url`,
      {
        method: "POST",
        body: JSON.stringify({ filename: file.name, content_type: contentType }),
      },
    );
    const uploaded = await fetch(signed.url, {
      method: "PUT",
      headers: { "Content-Type": contentType },
      body: file,
    });
    if (!uploaded.ok) throw new Error("Cloud Storage rejected the upload.");

    await api(
      `/api/applications/${applicationId}/documents/${documentType}/received`,
      {
        method: "POST",
        body: JSON.stringify({ filename: file.name, content_type: contentType }),
      },
    );
    feedback.textContent = `${file.name} uploaded. Processing document…`;
    try {
      await api(
        `/api/applications/${applicationId}/documents/${documentType}/process`,
        { method: "POST" },
      );
      await refreshApplication();
      setNotice(`${DOCUMENT_LABELS[documentType]} uploaded and processed.`, "success");
    } catch (processingError) {
      await refreshApplication();
      setNotice(
        `${DOCUMENT_LABELS[documentType]} uploaded, but processing needs attention: ${processingError.message}`,
        "error",
      );
    }
  } catch (error) {
    setNotice(error.message, "error");
    feedback.textContent = `Upload failed: ${error.message}`;
    feedback.className = "document-feedback error";
    uploadButton.disabled = false;
    uploadButton.textContent = "Upload";
  }
}

async function processDocument(record) {
  try {
    await api(
      `/api/applications/${applicationId}/documents/${record.document_type}/process`,
      { method: "POST" },
    );
    await refreshApplication();
    setNotice(`${DOCUMENT_LABELS[record.document_type]} processed.`, "success");
  } catch (error) {
    setNotice(error.message, "error");
  }
}

async function saveConsent() {
  try {
    applicationState = await api(
      `/api/applications/${applicationId}/credit-consent`,
      {
        method: "POST",
        body: JSON.stringify({ consent: byId("consent-checkbox").checked }),
      },
    );
    renderApplication();
    setNotice("Consent choice saved.", "success");
  } catch (error) {
    setNotice(error.message, "error");
  }
}

async function recordCreditResult(result) {
  try {
    applicationState = await api(
      `/api/applications/${applicationId}/credit-check`,
      { method: "POST", body: JSON.stringify({ result }) },
    );
    renderApplication();
    setNotice(`Simulated credit result recorded: ${result}.`, "success");
  } catch (error) {
    setNotice(error.message, "error");
  }
}

async function validatePackage() {
  try {
    applicationState = await api(
      `/api/applications/${applicationId}/validate`,
      { method: "POST" },
    );
    renderApplication();
    setNotice("Package validation completed.", "success");
  } catch (error) {
    setNotice(error.message, "error");
  }
}

async function submitPackage() {
  try {
    const receipt = await api(
      `/api/applications/${applicationId}/submit`,
      { method: "POST" },
    );
    const receiptPanel = byId("receipt");
    receiptPanel.replaceChildren();
    const title = document.createElement("strong");
    title.textContent = `Status: ${receipt.status}`;
    const reference = document.createElement("p");
    reference.textContent = `Reference: ${receipt.reference}`;
    receiptPanel.append(title, reference);
    receiptPanel.hidden = false;
    await refreshApplication();
    setNotice("The bank simulator acknowledged receipt.", "success");
  } catch (error) {
    setNotice(error.message, "error");
  }
}

byId("send-btn").addEventListener("click", sendMessage);
byId("msg-input").addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    sendMessage();
  }
});
byId("start-documents-btn").addEventListener("click", startDocumentCollection);
byId("save-consent-btn").addEventListener("click", saveConsent);
byId("credit-pass-btn").addEventListener("click", () => recordCreditResult("PASS"));
byId("credit-fail-btn").addEventListener("click", () => recordCreditResult("FAIL"));
byId("validate-btn").addEventListener("click", validatePackage);
byId("submit-btn").addEventListener("click", submitPackage);
byId("problem-btn").addEventListener("click", () => showQuickReplies(PROBLEM_OPTIONS));

refreshApplication()
  .then(() => {
    const firstName = applicationState.personal.first_name;
    const completion = applicationState.completion || {};
    const nextLabel = completion.next_missing_field_label;
    const greeting = firstName
      ? `Hello, ${firstName}. You’ve already made a good start and completed ${completion.fields_completed || 0} of the 20 details we need. I’m right here to help you finish the rest, one easy step at a time. Let’s begin with this: what is your ${nextLabel || "next missing detail"}?`
      : "Hello! I can help collect your loan application information and documents. I do not approve or decline applications. What is your first name?";
    appendMessage("agent", greeting);
    showQuickReplies(FIELD_QUICK_REPLIES[completion.next_missing_field] || []);
  })
  .catch((error) => setNotice(error.message, "error"));
