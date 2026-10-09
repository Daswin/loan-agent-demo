const API_BASE = window.LOAN_API_BASE || window.location.origin;
const token = new URLSearchParams(window.location.search).get("token");
const labels = {
  job_letter: "Job Letter",
  payslip_01: "Payslip",
  salary_assignment_form: "Salary Deduction / Assignment Form",
};
const cameraInput = document.getElementById("camera-input");
const fileInput = document.getElementById("file-input");
const uploadButton = document.getElementById("upload-btn");
const closeButton = document.getElementById("close-btn");
const statusElement = document.getElementById("status");
const preview = document.getElementById("preview");
const selectedFileElement = document.getElementById("selected-file");
let selectedFile = null;
let selectedContentType = null;
let previewUrl = null;

function documentContentType(file) {
  if (["application/pdf", "image/png", "image/jpeg"].includes(file.type)) {
    return file.type;
  }
  const extension = file.name.toLowerCase().split(".").pop();
  return {
    pdf: "application/pdf",
    png: "image/png",
    jpg: "image/jpeg",
    jpeg: "image/jpeg",
  }[extension] || null;
}

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
  cameraInput.disabled = false;
  fileInput.disabled = false;
}

function selectFile(file) {
  if (!file) return;
  const contentType = documentContentType(file);
  if (!contentType) {
    selectedFile = null;
    selectedContentType = null;
    uploadButton.disabled = true;
    statusElement.textContent = "Choose a PDF, PNG, or JPEG file.";
    statusElement.className = "error";
    return;
  }
  selectedFile = file;
  selectedContentType = contentType;
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  if (contentType.startsWith("image/")) {
    previewUrl = URL.createObjectURL(file);
    preview.src = previewUrl;
    preview.hidden = false;
    selectedFileElement.hidden = true;
  } else {
    preview.removeAttribute("src");
    preview.hidden = true;
    selectedFileElement.textContent = `Selected PDF: ${file.name}`;
    selectedFileElement.hidden = false;
  }
  uploadButton.disabled = false;
  statusElement.textContent = `${file.name} is ready to upload.`;
  statusElement.className = "";
}

cameraInput.addEventListener("change", () => selectFile(cameraInput.files[0]));
fileInput.addEventListener("change", () => selectFile(fileInput.files[0]));

uploadButton.addEventListener("click", async () => {
  const file = selectedFile;
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
          content_type: selectedContentType,
        }),
      },
    );
    const uploaded = await fetch(signed.url, {
      method: "PUT",
      headers: { "Content-Type": selectedContentType },
      body: file,
    });
    if (!uploaded.ok) throw new Error("The photo upload was rejected.");
    await api(`/api/mobile-upload-sessions/${encodeURIComponent(token)}/complete`, {
      method: "POST",
    });
    statusElement.textContent = "Upload complete. You may return to the other device.";
    statusElement.className = "success";
    cameraInput.disabled = true;
    fileInput.disabled = true;
    closeButton.textContent = "Done — close window";
  } catch (error) {
    statusElement.textContent = error.message;
    statusElement.className = "error";
  }
});

closeButton.addEventListener("click", () => {
  window.close();
  window.setTimeout(() => {
    if (document.visibilityState === "visible") {
      statusElement.textContent = "You can now close this browser tab or window.";
      statusElement.className = "success";
      closeButton.textContent = "Ready to close";
    }
  }, 200);
});

window.addEventListener("beforeunload", () => {
  if (previewUrl) URL.revokeObjectURL(previewUrl);
});

initialize().catch((error) => {
  document.getElementById("instructions").textContent = "This upload link is unavailable.";
  statusElement.textContent = error.message;
  statusElement.className = "error";
});
