from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class FrontendContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (PROJECT_ROOT / "index.html").read_text(encoding="utf-8")
        cls.javascript = (PROJECT_ROOT / "app.js").read_text(encoding="utf-8")
        cls.landing = (
            PROJECT_ROOT / "landing" / "src" / "App.tsx"
        ).read_text(encoding="utf-8")
        cls.dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(
            encoding="utf-8"
        )
        cls.nginx_config = (PROJECT_ROOT / "default.conf").read_text(
            encoding="utf-8"
        )

    def test_all_required_documents_are_present(self):
        for label in (
            "Job Letter",
            "Payslip",
            "Salary Deduction / Assignment Form",
        ):
            self.assertIn(label, self.javascript)

    def test_frontend_uses_application_aware_api_contract(self):
        self.assertIn("application_id: applicationId", self.javascript)
        self.assertIn("/api/applications", self.javascript)
        self.assertIn("/upload-url", self.javascript)
        self.assertIn("/credit-consent", self.javascript)
        self.assertIn("/credit-check", self.javascript)
        self.assertIn("/validate", self.javascript)
        self.assertIn("/submit", self.javascript)

    def test_operator_controls_explain_non_decision_semantics(self):
        self.assertIn("Demo operator controls", self.html)
        self.assertIn("does not approve or decline", self.html)
        self.assertIn("Process document", self.javascript)
        self.assertIn("/process", self.javascript)

    def test_messages_are_rendered_without_inner_html(self):
        self.assertNotIn("innerHTML", self.javascript)
        self.assertIn("message.textContent = text", self.javascript)

    def test_obsolete_generic_upload_contract_is_absent(self):
        self.assertNotIn("/api/get-signed-url", self.javascript)
        self.assertNotIn("gcs_uri", self.javascript)
        self.assertNotIn("System: Client uploaded", self.javascript)

    def test_landing_page_continues_to_application_route(self):
        self.assertIn("/application/?", self.landing)
        self.assertIn("customer: modalCustomer.id", self.landing)
        self.assertIn("loanAmount: String(loanAmount)", self.landing)

    def test_selected_customer_is_saved_through_backend(self):
        self.assertIn("CUSTOMER_PROFILES", self.javascript)
        self.assertIn("profile_id: customerId", self.javascript)
        self.assertIn("requested_amount: selectedLoanAmount", self.javascript)
        self.assertIn("loan-agent-application-id:v3:${customerId}", self.javascript)

    def test_container_serves_landing_and_application(self):
        self.assertIn("FROM node:20-alpine AS landing-builder", self.dockerfile)
        self.assertIn("/landing/dist/ /usr/share/nginx/html/", self.dockerfile)
        self.assertIn(
            "/usr/share/nginx/html/application/index.html",
            self.dockerfile,
        )

    def test_document_uploader_does_not_overlay_workflow_controls(self):
        self.assertIn(".documents-card { position: static; }", self.html)
        self.assertNotIn(".documents-card { position: sticky", self.html)

    def test_document_upload_shows_inline_progress_and_errors(self):
        self.assertIn("document-feedback", self.javascript)
        self.assertIn('uploadButton.textContent = "Uploading…"', self.javascript)
        self.assertIn("Upload failed:", self.javascript)

    def test_navigation_and_conversation_choice_controls_are_present(self):
        self.assertIn('class="back-link" href="/"', self.html)
        self.assertIn('id="problem-btn"', self.html)
        self.assertIn('id="quick-replies"', self.html)
        self.assertIn("PROBLEM_OPTIONS", self.javascript)
        self.assertIn("FIELD_QUICK_REPLIES", self.javascript)
        self.assertNotIn("inferReplyOptions", self.javascript)
        self.assertNotIn('return ["Yes", "No"]', self.javascript)
        self.assertIn('["Agree", "Disagree"]', self.javascript)

    def test_demo_document_button_preserves_manual_upload_workflow(self):
        self.assertIn('id="auto-documents-btn"', self.html)
        self.assertIn("/demo-documents", self.javascript)
        self.assertIn('input.type = "file"', self.javascript)
        self.assertIn("uploadDocument(", self.javascript)
        self.assertIn("Submit package", self.html)

    def test_manual_and_inactivity_reset_controls_are_present(self):
        self.assertIn('id="reset-application-btn"', self.html)
        self.assertIn("/reset", self.javascript)
        self.assertIn("/activity", self.javascript)
        self.assertIn("60_000", self.javascript)
        self.assertIn("five minutes of inactivity", self.javascript)

    def test_application_shell_avoids_mixed_cached_frontend_versions(self):
        self.assertIn(
            'byId("reset-application-btn")?.addEventListener',
            self.javascript,
        )
        self.assertIn("location /application/", self.nginx_config)
        self.assertIn("no-store, no-cache, must-revalidate", self.nginx_config)


if __name__ == "__main__":
    unittest.main()
