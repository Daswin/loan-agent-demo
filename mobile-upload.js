const API_BASE = window.LOAN_API_BASE || window.location.origin;
const token = new URLSearchParams(window.location.search).get("token");
const labels = {
  job_letter: "Job Letter",
  payslip_01: "Payslip",
  salary_assignment_form: "Salary Deduction / Assignment Form",
};
const input = document.getElementById("camera-input");
const uploadButton = document.getElementById("upload-btn");
const statusElement = document.getElementById("status");
const preview = document.getElementById("preview");

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {}),
    },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || `Request failed (${response.status})`);
  }
  return response.json();
}

async function initialize() {
  if (!token) throw new Error("The secure upload token is missing.");
  const session = await api(`/api/mobile-upload-sessions/${encodeURIComponent(token)}`);
  if (session.completed) {
    document.getElementById("instructions").textContent = "This document photo has already been uploaded.";
    statusElement.textContent = "You may close this page.";
    statusElement.className = "success";
    return;
  }
  document.getElementById("instructions").textContent =
    `Take a clear, well-lit photo of the ${labels[session.document_type] || "document"}. Keep all four corners visible.`;
  input.disabled = false;
}

input.addEventListener("change", () => {
  const file = input.files[0];
  if (!file) return;
  preview.src = URL.createObjectURL(file);
  preview.hidden = false;
  uploadButton.disabled = false;
  statusElement.textContent = `${file.name} is ready to upload.`;
  statusElement.className = "";
});

uploadButton.addEventListener("click", async () => {
  const file = input.files[0];
  if (!file) return;
  uploadButton.disabled = true;
  statusElement.textContent = "Uploading securely…";
  try {
    const signed = await api(
      `/api/mobile-upload-sessions/${encodeURIComponent(token)}/upload-url`,
      {
        method: "POST",
        body: JSON.stringify({
          filename: file.name || `document-${Date.now()}.jpg`,
          content_type: file.type || "image/jpeg",
        }),
      },
    );
    const uploaded = await fetch(signed.url, {
      method: "PUT",
      headers: { "Content-Type": file.type || "image/jpeg" },
      body: file,
    });
    if (!uploaded.ok) throw new Error("The photo upload was rejected.");
    await api(`/api/mobile-upload-sessions/${encodeURIComponent(token)}/complete`, {
      method: "POST",
    });
    statusElement.textContent = "Upload complete. You may return to the other device.";
    statusElement.className = "success";
    input.disabled = true;
  } catch (error) {
    statusElement.textContent = error.message;
    statusElement.className = "error";
  }
});

initialize().catch((error) => {
  document.getElementById("instructions").textContent = "This upload link is unavailable.";
  statusElement.textContent = error.message;
  statusElement.className = "error";
});
