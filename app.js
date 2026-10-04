const API_BASE = window.LOAN_API_BASE || window.location.origin;
const SESSION_KEY = "loan-agent-session-id";
const TUTORIAL_KEY = "loan-agent-tutorial-complete:v1";
let sessionId = localStorage.getItem(SESSION_KEY) || crypto.randomUUID();

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

const APPLICATION_REVIEW_SECTIONS = [
  {
    title: "Identity",
    fields: [
      ["applicant.identity.first_name", "First name"],
      ["applicant.identity.last_name", "Last name"],
      ["applicant.identity.date_of_birth", "Date of birth"],
      ["applicant.identity.trn_tax_id", "TRN"],
      ["applicant.identity.primary_id.type", "Photo ID type"],
      ["applicant.identity.primary_id.number", "Photo ID number"],
    ],
  },
  {
    title: "Contact and address",
    fields: [
      ["applicant.contact.personal_email", "Personal email address"],
      ["applicant.contact.mobile_phone", "Mobile phone number"],
      ["applicant.current_address.address_line_1", "Current street address"],
      ["applicant.current_address.city_town", "Current city or town"],
      ["applicant.current_address.parish_state", "Current parish or state"],
    ],
  },
  {
    title: "Employment and income",
    fields: [
      ["applicant.employment.employment_status", "Employment status"],
      ["applicant.employment.employer_name", "Employer name"],
      ["applicant.employment.job_title", "Job title"],
      ["applicant.income.gross_monthly_salary", "Gross monthly salary"],
      ["applicant.income.net_monthly_salary", "Net monthly salary"],
      ["applicant.banking.primary_bank", "Primary bank"],
    ],
  },
  {
    title: "Loan request",
    fields: [
      ["loan_request.requested_amount", "Requested loan amount"],
      ["loan_request.loan_purpose", "Loan purpose"],
      ["loan_request.requested_term_months", "Requested loan term (months)"],
    ],
  },
];

const MONEY_FIELDS = new Set([
  "applicant.income.gross_monthly_salary",
  "applicant.income.net_monthly_salary",
  "loan_request.requested_amount",
]);

const PROBLEM_OPTIONS = [
  "Problem: My documents are delayed",
  "Problem: My employer will not sign the salary assignment form",
  "Problem: I cannot upload a document",
  "Problem: Some application information is incorrect",
  "Problem: I have a question about credit consent",
];

let applicationId = localStorage.getItem(APPLICATION_KEY);
let applicationState = null;
localStorage.setItem(SESSION_KEY, sessionId);

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
    let details = null;
    try {
      const error = await response.json();
      details = error.detail || null;
      message = typeof details === "object" && details
        ? details.message || message
        : details || message;
    } catch (_) {
      // Preserve the status-based message for non-JSON errors.
    }
    const apiError = new Error(message);
    apiError.status = response.status;
    apiError.details = details;
    throw apiError;
  }

  return response.status === 204 ? null : response.json();
}

function setNotice(message, kind = "") {
  const notice = byId("notice");
  notice.textContent = message;
  notice.className = `global-notice${kind ? ` ${kind}` : ""}`;
}

function activateWorkspaceTab(targetId) {
  document.querySelectorAll(".tab-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.id === targetId);
  });

  document.querySelectorAll("[data-tab-target]").forEach((button) => {
    const isActive = button.dataset.tabTarget === targetId;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-selected", String(isActive));
  });

  if (window.matchMedia("(max-width: 920px)").matches) {
    document.querySelector(".assistant-shell")?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }
}

const TUTORIAL_STEPS = [
  { selector: '.header-link[href="/"], .mobile-back', title: "Customer selection", description: "Use this option to return to the customer list without using the browser back button." },
  { selector: ".progress-rail", title: "Application progress", description: "This guide tracks information, documents, the simulated credit check, and submission without crowding the conversation." },
  { selector: '[data-tab-target="chat-panel"]', tab: "chat-panel", title: "Chat", description: "The assistant collects one missing detail at a time and can answer questions while you complete the application." },
  { selector: "#chat-window", tab: "chat-panel", title: "Conversation", description: "Application questions and your answers appear here. Suggested responses are shown only for categorical questions." },
  { selector: ".composer", tab: "chat-panel", title: "Your response", description: "Type an answer or question here, then use the blue send button." },
  { selector: "#problem-btn", tab: "chat-panel", title: "Need help?", description: "Choose this when documentation, employer, upload, or consent issues are getting in the way." },
  { selector: '[data-tab-target="documents-panel"]', tab: "documents-panel", title: "Documents", description: "Open this tab to upload the three required documents. Uploads are available immediately." },
  { selector: "#document-list", tab: "documents-panel", title: "Required documents", description: "Choose a PDF or image for each slot. Uploaded files are processed through the prototype document workflow." },
  { selector: ".camera-option", tab: "documents-panel", mobileOnly: true, title: "Photograph a document", description: "On a phone, this opens the rear camera so you can photograph and upload a document directly." },
  { selector: "#auto-documents-btn", tab: "documents-panel", title: "Demo shortcut", description: "For stakeholder testing, this creates and uploads sample documents. Manual upload remains available." },
  { selector: '[data-tab-target="application-panel"]', tab: "application-panel", title: "Application controls", description: "This tab contains consent, simulated credit evaluation, validation, and submission." },
  { selector: "#consent-checkbox", tab: "application-panel", title: "Credit consent", description: "The applicant must explicitly provide consent before the simulated credit check can run." },
  { selector: "#credit-pass-btn", tab: "application-panel", title: "Simulated credit result", description: "The operator records PASS or FAIL here. This is not underwriting and does not approve or decline the loan." },
  { selector: "#validate-btn", tab: "application-panel", title: "Validate", description: "Validation checks that required information, documents, consent, and workflow steps are complete." },
  { selector: "#submit-btn", tab: "application-panel", title: "Submit", description: "Submission sends the completed package to the simulated bank, which acknowledges receipt only." },
  { selector: ".review-tab", title: "Review", description: "Open Review at any time to see all recorded application information and document statuses." },
];

let tutorialIndex = 0;
let tutorialTarget = null;

function visibleTutorialTarget(selector) {
  return [...document.querySelectorAll(selector)].find((element) => {
    const style = window.getComputedStyle(element);
    return style.display !== "none" && style.visibility !== "hidden" && element.getClientRects().length;
  }) || null;
}

function positionTutorial() {
  if (!tutorialTarget) return;
  const rect = tutorialTarget.getBoundingClientRect();
  const padding = 7;
  const highlight = byId("tutorial-highlight");
  highlight.style.left = `${Math.max(5, rect.left - padding)}px`;
  highlight.style.top = `${Math.max(5, rect.top - padding)}px`;
  highlight.style.width = `${Math.min(window.innerWidth - 10, rect.width + padding * 2)}px`;
  highlight.style.height = `${Math.min(window.innerHeight - 10, rect.height + padding * 2)}px`;

  const card = byId("tutorial-card");
  const cardWidth = Math.min(360, window.innerWidth - 28);
  const left = Math.min(
    window.innerWidth - cardWidth - 14,
    Math.max(14, rect.left + rect.width / 2 - cardWidth / 2),
  );
  card.style.left = `${left}px`;
  card.style.width = `${cardWidth}px`;
  const cardHeight = card.offsetHeight || 230;
  const below = rect.bottom + 18;
  card.style.top = `${below + cardHeight <= window.innerHeight - 12
    ? below
    : Math.max(12, rect.top - cardHeight - 18)}px`;
}

function showTutorialStep(direction = 1) {
  while (tutorialIndex >= 0 && tutorialIndex < TUTORIAL_STEPS.length) {
    const step = TUTORIAL_STEPS[tutorialIndex];
    if (step.mobileOnly && !window.matchMedia("(max-width: 920px)").matches) {
      tutorialIndex += direction;
      continue;
    }
    if (step.tab) activateWorkspaceTab(step.tab);
    tutorialTarget = visibleTutorialTarget(step.selector);
    if (!tutorialTarget) {
      tutorialIndex += direction;
      continue;
    }
    tutorialTarget.scrollIntoView({ behavior: "smooth", block: "center" });
    byId("tutorial-step").textContent = `Step ${tutorialIndex + 1} of ${TUTORIAL_STEPS.length}`;
    byId("tutorial-title").textContent = step.title;
    byId("tutorial-description").textContent = step.description;
    byId("tutorial-back").disabled = tutorialIndex === 0;
    byId("tutorial-next").textContent = tutorialIndex === TUTORIAL_STEPS.length - 1
      ? "Finish"
      : "Next";
    window.setTimeout(positionTutorial, 260);
    return;
  }
  finishTutorial();
}

function startTutorial() {
  tutorialIndex = 0;
  byId("tutorial-overlay").hidden = false;
  showTutorialStep();
}

function finishTutorial() {
  byId("tutorial-overlay").hidden = true;
  tutorialTarget = null;
  localStorage.setItem(TUTORIAL_KEY, "true");
}

function maybeStartTutorial() {
  if (!localStorage.getItem(TUTORIAL_KEY) && byId("tutorial-overlay").hidden) {
    startTutorial();
  }
}

function appendMessage(sender, text) {
  const message = document.createElement("div");
  message.className = `message ${sender}`;
  message.textContent = text;
  const chatWindow = byId("chat-window");
  chatWindow.appendChild(message);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function startFreshConversation() {
  byId("chat-window").replaceChildren();
  showQuickReplies();
  const receipt = byId("receipt");
  receipt.replaceChildren();
  receipt.hidden = true;
  sessionId = crypto.randomUUID();
  localStorage.setItem(SESSION_KEY, sessionId);

  const firstName = applicationState.personal.first_name;
  const completion = applicationState.completion || {};
  const nextQuestion = completion.next_missing_field_question;
  let greeting;
  let greetingReplies = [];
  if (!firstName) {
    greeting = "Hello! I can help collect your loan application information and documents. I do not approve or decline applications. What is your first name?";
  } else if (nextQuestion) {
    greeting = `Hello, ${firstName}. You've already made a good start and completed ${completion.fields_completed || 0} of the 20 details we need. I'm here to help you finish the rest, one step at a time. Let's begin with this: ${nextQuestion}`;
    greetingReplies = FIELD_QUICK_REPLIES[completion.next_missing_field] || [];
  } else if (!applicationState.credit_bureau.consent) {
    greeting = `Hello, ${firstName}. Your application information is complete. Please upload the three required documents next. Before we run the simulated credit-bureau check, do you consent to that check?`;
    greetingReplies = ["Agree", "Disagree"];
  } else {
    greeting = `Hello, ${firstName}. Your application information is complete and your credit-bureau consent is recorded. Please upload the three required documents next.`;
  }
  appendMessage("agent", greeting);
  showQuickReplies(greetingReplies);
}

function showQuickReplies(options = []) {
  byId("quick-replies")?.remove();
  if (!options.length) return;

  const container = document.createElement("div");
  container.id = "quick-replies";
  container.className = "quick-replies";
  container.setAttribute("aria-label", "Suggested responses");
  options.forEach((option) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "quick-reply";
    button.textContent = option;
    button.addEventListener("click", () => sendMessage(option));
    container.appendChild(button);
  });
  const chatWindow = byId("chat-window");
  chatWindow.appendChild(container);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function getApplicationValue(path) {
  return path.split(".").reduce(
    (value, part) => value && value[part],
    applicationState.application_data,
  );
}

function formatReviewValue(path, value) {
  if (MONEY_FIELDS.has(path) && typeof value === "number") {
    return new Intl.NumberFormat("en-JM", {
      style: "currency",
      currency: "JMD",
      maximumFractionDigits: 2,
    }).format(value);
  }
  if (path === "applicant.identity.date_of_birth" && /^\d{4}-\d{2}-\d{2}$/.test(String(value))) {
    const [year, month, day] = String(value).split("-");
    return `${day}/${month}/${year}`;
  }
  return String(value);
}

function appendReviewStat(container, label, value) {
  const stat = document.createElement("div");
  stat.className = "review-stat";
  const statLabel = document.createElement("span");
  statLabel.textContent = label;
  const statValue = document.createElement("strong");
  statValue.textContent = value;
  stat.append(statLabel, statValue);
  container.appendChild(stat);
}

function renderApplicationReview() {
  if (!applicationState) return;
  const completion = applicationState.completion || {};
  const providedFields = new Set(applicationState.provided_fields || []);
  const summary = byId("review-summary");
  summary.replaceChildren();
  appendReviewStat(
    summary,
    "Information",
    `${completion.fields_completed || 0} of ${completion.fields_required || 20} complete`,
  );
  appendReviewStat(
    summary,
    "Documents",
    `${completion.documents_completed || 0} of ${completion.documents_required || 3} complete`,
  );
  appendReviewStat(
    summary,
    "Credit consent",
    applicationState.credit_bureau.consent ? "Provided" : "Not provided",
  );

  const fieldsContainer = byId("review-fields");
  fieldsContainer.replaceChildren();
  APPLICATION_REVIEW_SECTIONS.forEach((reviewSection) => {
    const section = document.createElement("section");
    section.className = "review-section";
    const heading = document.createElement("h3");
    heading.textContent = reviewSection.title;
    const list = document.createElement("dl");
    list.className = "review-grid";

    reviewSection.fields.forEach(([path, label]) => {
      const field = document.createElement("div");
      const completed = providedFields.has(path);
      field.className = `review-field${completed ? "" : " missing"}`;
      const term = document.createElement("dt");
      term.textContent = label;
      const description = document.createElement("dd");
      const value = getApplicationValue(path);
      description.textContent = completed && value !== "" && value !== null && value !== undefined
        ? formatReviewValue(path, value)
        : "Not yet provided";
      field.append(term, description);
      list.appendChild(field);
    });
    section.append(heading, list);
    fieldsContainer.appendChild(section);
  });

  const documents = byId("review-documents");
  documents.replaceChildren();
  applicationState.documents.forEach((record) => {
    const row = document.createElement("div");
    row.className = "review-document";
    const label = document.createElement("span");
    label.textContent = DOCUMENT_LABELS[record.document_type] || record.document_type;
    const status = document.createElement("strong");
    status.textContent = record.status;
    row.append(label, status);
    documents.appendChild(row);
  });
}

function openApplicationReview() {
  renderApplicationReview();
  byId("review-dialog").showModal();
}

function renderProgressRail() {
  const completion = applicationState.completion || {};
  const stages = [
    {
      id: "stage-information",
      complete: (completion.information_percent || 0) === 100,
    },
    {
      id: "stage-documents",
      complete: (completion.documents_percent || 0) === 100,
    },
    {
      id: "stage-credit",
      complete: Boolean(
        applicationState.credit_bureau.consent
        && applicationState.credit_bureau.result,
      ),
    },
    {
      id: "stage-submission",
      complete: applicationState.status === "SUBMITTED",
    },
  ];
  const currentIndex = stages.findIndex((stage) => !stage.complete);
  stages.forEach((stage, index) => {
    const element = byId(stage.id);
    element.classList.toggle("complete", stage.complete);
    element.classList.toggle("current", index === currentIndex);
    element.classList.toggle("pending", !stage.complete && index !== currentIndex);
    const dot = element.querySelector(".stage-dot");
    dot.textContent = stage.complete ? "✓" : String(index + 1);
  });
}

function showStatusDialog({ title, subtitle, message, items = [], note = "" }) {
  byId("status-dialog-title").textContent = title;
  byId("status-dialog-subtitle").textContent = subtitle;
  byId("status-dialog-message").textContent = message;
  const list = byId("status-dialog-items");
  list.replaceChildren();
  items.forEach((item) => {
    const listItem = document.createElement("li");
    listItem.textContent = item;
    list.appendChild(listItem);
  });
  list.hidden = items.length === 0;
  const noteElement = byId("status-dialog-note");
  noteElement.textContent = note;
  noteElement.hidden = !note;
  byId("status-dialog").showModal();
}

function showIncompleteApplicationDialog(error) {
  const missingItems = error.details?.missing_items || [];
  showStatusDialog({
    title: "Application needs attention",
    subtitle: "Validation could not be completed.",
    message: "Please complete the following items before validating and submitting the application:",
    items: missingItems.length ? missingItems : [error.message],
  });
}

function showCreditFailDialog() {
  showStatusDialog({
    title: "Credit screening result",
    subtitle: "The simulated credit screening returned FAIL.",
    message: "This screening result does not approve or decline your application. You may wish to discuss one of these alternatives with a loan officer:",
    items: [
      "Pay Advance",
      "Credit Card",
      "Fast Cash",
      "A smaller personal loan",
    ],
    note: "Availability and eligibility for any alternative product would require a separate assessment by the bank.",
  });
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
  if (applicationState.status === "IN_PROGRESS") {
    applicationState = await api(
      `/api/applications/${applicationId}/documents/start`,
      { method: "POST" },
    );
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
  renderProgressRail();
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
  const creditCheckFailed = applicationState.credit_bureau.result === "FAIL";
  byId("validate-btn").disabled =
    applicationState.status !== "VALIDATION_REQUIRED" || creditCheckFailed;
  byId("submit-btn").disabled =
    applicationState.status !== "READY_FOR_SUBMISSION" || creditCheckFailed;
  byId("validate-action").classList.toggle("credit-blocked", creditCheckFailed);
  byId("submit-action").classList.toggle("credit-blocked", creditCheckFailed);
  byId("auto-documents-btn").disabled = ![
    "IN_PROGRESS",
    "DOCUMENTS_REQUIRED",
    "DOCUMENTS_PROCESSING",
  ].includes(applicationState.status);
  renderDocuments();
  if (byId("review-dialog").open) renderApplicationReview();
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

    const cameraInput = document.createElement("input");
    cameraInput.type = "file";
    cameraInput.accept = "image/*";
    cameraInput.setAttribute("capture", "environment");
    cameraInput.className = "camera-input";
    cameraInput.disabled = input.disabled;
    const cameraButton = document.createElement("button");
    cameraButton.type = "button";
    cameraButton.className = "camera-option secondary";
    cameraButton.disabled = input.disabled;
    cameraButton.textContent = "Take photo of document";
    cameraButton.addEventListener("click", () => cameraInput.click());
    cameraInput.addEventListener("change", () => {
      if (cameraInput.files.length) {
        uploadDocument(
          record.document_type,
          cameraInput,
          cameraButton,
          feedback,
        );
      }
    });
    controls.append(cameraInput, cameraButton);

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
        session_id: sessionId,
        application_id: applicationId,
        message,
      }),
    });
    appendMessage("agent", result.reply || "Your application was updated.");
    await refreshApplication();
    const problemMentioned = /problem|issue|trouble|delay|cannot|can't|won't|will not|refus|help/i.test(message);
    showQuickReplies(
      problemMentioned ? PROBLEM_OPTIONS : (result.quick_replies || []),
    );
  } catch (error) {
    appendMessage("agent", `Unable to continue: ${error.message}`);
  } finally {
    byId("send-btn").disabled = false;
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
  const idleButtonLabel = uploadButton.textContent;
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
    uploadButton.textContent = idleButtonLabel;
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

async function createDemoDocuments() {
  const button = byId("auto-documents-btn");
  button.disabled = true;
  button.textContent = "Creating demo documents...";
  setNotice("Creating and uploading three demo documents...");
  try {
    applicationState = await api(
      `/api/applications/${applicationId}/demo-documents`,
      { method: "POST" },
    );
    renderApplication();
    setNotice(
      "Demo job letter, payslip, and salary assignment form uploaded.",
      "success",
    );
  } catch (error) {
    setNotice(error.message, "error");
  } finally {
    button.textContent = "Create demo documents";
    renderApplication();
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
    if (result === "FAIL") {
      showCreditFailDialog();
    } else {
      showStatusDialog({
        title: "Credit screening recorded",
        subtitle: "The simulated credit check returned PASS.",
        message: "The screening result has been recorded. This does not approve the loan or constitute an underwriting decision.",
      });
    }
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
    showStatusDialog({
      title: "Application validated",
      subtitle: "The required workflow checks are complete.",
      message: "The application package is ready for submission. Validation confirms completeness only and is not a loan approval or underwriting decision.",
    });
  } catch (error) {
    setNotice(error.message, "error");
    if (error.details?.missing_items) showIncompleteApplicationDialog(error);
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
    showStatusDialog({
      title: "Application submitted",
      subtitle: "The bank simulator acknowledged receipt.",
      message: `Status: ${receipt.status}. Reference: ${receipt.reference}. This confirms receipt only and is not a loan approval.`,
    });
  } catch (error) {
    setNotice(error.message, "error");
    if (error.details?.missing_items) showIncompleteApplicationDialog(error);
  }
}

let heartbeatInProgress = false;
let inactivityWarningTimer = null;
let inactivityResetTimer = null;
let inactivityCountdownTimer = null;
let inactivityDeadline = 0;
let lastActivitySyncAt = 0;

function closeInactivityDialog() {
  const dialog = byId("inactivity-dialog");
  if (dialog.open) dialog.close();
  window.clearInterval(inactivityCountdownTimer);
}

function showInactivityDialog(mode = "intro") {
  const warning = mode === "warning";
  byId("inactivity-title").textContent = warning
    ? "Are you still working?"
    : "A quick note before we begin";
  byId("inactivity-message").textContent = warning
    ? "This application is about to return to its original demo state because no activity has been detected."
    : "For this shared demonstration, an application returns to its original state after five minutes without activity.";
  byId("inactivity-action-btn").textContent = warning ? "I'm still here" : "Continue";
  const countdown = byId("inactivity-countdown");
  countdown.hidden = !warning;
  if (warning) {
    const updateCountdown = () => {
      const seconds = Math.max(0, Math.ceil((inactivityDeadline - Date.now()) / 1000));
      countdown.textContent = `Resetting in ${seconds} second${seconds === 1 ? "" : "s"}.`;
    };
    updateCountdown();
    window.clearInterval(inactivityCountdownTimer);
    inactivityCountdownTimer = window.setInterval(updateCountdown, 1000);
  }
  const dialog = byId("inactivity-dialog");
  if (!dialog.open) dialog.showModal();
}

function scheduleInactivityTimers() {
  window.clearTimeout(inactivityWarningTimer);
  window.clearTimeout(inactivityResetTimer);
  window.clearInterval(inactivityCountdownTimer);
  inactivityDeadline = Date.now() + 300_000;
  inactivityWarningTimer = window.setTimeout(
    () => showInactivityDialog("warning"),
    240_000,
  );
  inactivityResetTimer = window.setTimeout(recordActivity, 300_000);
}

async function recordActivity() {
  if (!applicationId || document.visibilityState !== "visible" || heartbeatInProgress) {
    return;
  }
  heartbeatInProgress = true;
  try {
    const result = await api(
      `/api/applications/${applicationId}/activity`,
      { method: "POST" },
    );
    if (result.reset_performed) {
      applicationState = result.application;
      renderApplication();
      startFreshConversation(true);
      byId("inactivity-title").textContent = "Application reset";
      byId("inactivity-message").textContent =
        "The application returned to its original demo state after five minutes without activity. You can continue whenever you're ready.";
      byId("inactivity-countdown").hidden = true;
      byId("inactivity-action-btn").textContent = "Continue";
      const dialog = byId("inactivity-dialog");
      if (!dialog.open) dialog.showModal();
    }
  } catch (error) {
    console.warn("Unable to record application activity.", error);
  } finally {
    heartbeatInProgress = false;
    scheduleInactivityTimers();
  }
}

function noteCustomerActivity(syncWithBackend = true) {
  scheduleInactivityTimers();
  if (!syncWithBackend || Date.now() - lastActivitySyncAt < 30_000) return;
  lastActivitySyncAt = Date.now();
  recordActivity();
}

byId("send-btn").addEventListener("click", sendMessage);
byId("msg-input").addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    sendMessage();
  }
});
byId("auto-documents-btn").addEventListener("click", createDemoDocuments);
byId("save-consent-btn").addEventListener("click", saveConsent);
byId("credit-pass-btn").addEventListener("click", () => recordCreditResult("PASS"));
byId("credit-fail-btn").addEventListener("click", () => recordCreditResult("FAIL"));
byId("validate-btn").addEventListener("click", validatePackage);
byId("submit-btn").addEventListener("click", submitPackage);
byId("problem-btn").addEventListener("click", () => showQuickReplies(PROBLEM_OPTIONS));
byId("close-review-btn").addEventListener("click", () => byId("review-dialog").close());
byId("close-status-dialog-btn").addEventListener("click", () => byId("status-dialog").close());
byId("inactivity-action-btn").addEventListener("click", () => {
  closeInactivityDialog();
  noteCustomerActivity(true);
});
document.querySelectorAll("[data-tab-target]").forEach((button) => {
  button.addEventListener("click", () => activateWorkspaceTab(button.dataset.tabTarget));
});
document.querySelectorAll(".review-tab").forEach((button) => {
  button.addEventListener("click", openApplicationReview);
});
document.querySelectorAll(".tutorial-launch").forEach((button) => {
  button.addEventListener("click", startTutorial);
});
byId("tutorial-next").addEventListener("click", () => {
  if (tutorialIndex === TUTORIAL_STEPS.length - 1) {
    finishTutorial();
    return;
  }
  tutorialIndex += 1;
  showTutorialStep(1);
});
byId("tutorial-back").addEventListener("click", () => {
  tutorialIndex -= 1;
  showTutorialStep(-1);
});
byId("tutorial-skip").addEventListener("click", finishTutorial);
byId("inactivity-dialog").addEventListener("close", () => {
  window.setTimeout(maybeStartTutorial, 180);
});
window.addEventListener("resize", positionTutorial);
document.addEventListener("scroll", positionTutorial, true);
document.addEventListener("pointerdown", () => noteCustomerActivity(true), { passive: true });
document.addEventListener("keydown", (event) => {
  noteCustomerActivity(true);
  if (event.key === "Escape" && !byId("tutorial-overlay").hidden) {
    finishTutorial();
  }
});

refreshApplication()
  .then(() => {
    startFreshConversation(Boolean(applicationState.last_reset_at));
    scheduleInactivityTimers();
    showInactivityDialog("intro");
  })
  .catch((error) => setNotice(error.message, "error"));
