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

    def test_greeting_uses_backend_supplied_field_question(self):
        self.assertIn("completion.next_missing_field_question", self.javascript)
        self.assertNotIn("what is your ${nextLabel}", self.javascript)
        self.assertIn("/api/applications", self.javascript)
        self.assertIn("/upload-url", self.javascript)
        self.assertIn("/credit-consent", self.javascript)
        self.assertIn("/credit-check", self.javascript)
        self.assertIn("/validate", self.javascript)
        self.assertIn("/submit", self.javascript)

    def test_operator_controls_explain_non_decision_semantics(self):
        self.assertIn("Simulated Credit Bureau Evaluation", self.html)
        self.assertIn("Credit Check Pass", self.html)
        self.assertIn("Credit Check Failed", self.html)
        self.assertIn("does not approve or decline", self.html)
        self.assertIn("Process document", self.javascript)
        self.assertIn("/process", self.javascript)

    def test_failed_credit_check_blocks_workflow_actions_with_tooltips(self):
        self.assertIn('id="validate-action"', self.html)
        self.assertIn('id="submit-action"', self.html)
        self.assertIn("failed simulated credit check prevents", self.html)
        self.assertIn('credit_bureau.result === "FAIL"', self.javascript)
        self.assertIn('classList.toggle("credit-blocked", creditCheckFailed)', self.javascript)

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
        self.assertIn('class="header-link" href="/"', self.html)

    def test_responsive_workspace_navigation_is_present(self):
        self.assertIn('data-tab-target="chat-panel"', self.html)
        self.assertIn('data-tab-target="documents-panel"', self.html)
        self.assertIn('data-tab-target="application-panel"', self.html)
        self.assertIn('class="mobile-nav"', self.html)
        self.assertIn('document.querySelectorAll("[data-tab-target]")', self.javascript)
        self.assertIn('id="problem-btn"', self.html)
        self.assertNotIn('id="quick-replies"', self.html)
        self.assertIn('container.id = "quick-replies"', self.javascript)
        self.assertIn("chatWindow.appendChild(container)", self.javascript)
        self.assertIn("PROBLEM_OPTIONS", self.javascript)
        self.assertIn("FIELD_QUICK_REPLIES", self.javascript)
        self.assertNotIn("inferReplyOptions", self.javascript)
        self.assertNotIn('return ["Yes", "No"]', self.javascript)
        self.assertIn('["Agree", "Disagree"]', self.javascript)

    def test_application_review_is_always_available_as_a_tab(self):
        self.assertNotIn('id="review-application-btn"', self.html)
        self.assertIn('class="tab-button review-tab"', self.html)
        self.assertIn('id="review-dialog"', self.html)
        self.assertIn("APPLICATION_REVIEW_SECTIONS", self.javascript)
        self.assertIn("applicationState.provided_fields", self.javascript)
        self.assertIn("applicationState.documents", self.javascript)
        self.assertIn("openApplicationReview", self.javascript)

    def test_validation_and_credit_fail_modals_are_present(self):
        self.assertIn("Validate Application", self.html)
        self.assertIn("Submit Application", self.html)
        self.assertIn('id="status-dialog"', self.html)
        self.assertIn("showIncompleteApplicationDialog", self.javascript)
        self.assertIn("error.details?.missing_items", self.javascript)
        self.assertIn("showCreditFailDialog", self.javascript)
        for product in ("Pay Advance", "Credit Card", "Fast Cash", "A smaller personal loan"):
            self.assertIn(product, self.javascript)
        self.assertIn("does not approve or decline", self.javascript)

    def test_successful_workflow_actions_show_confirmation_modals(self):
        for title in (
            "Credit screening recorded",
            "Application validated",
            "Application submitted",
        ):
            self.assertIn(title, self.javascript)
        self.assertIn("This does not approve the loan", self.javascript)
        self.assertIn("not a loan approval", self.javascript)

    def test_demo_document_button_preserves_manual_upload_workflow(self):
        self.assertIn('id="auto-documents-btn"', self.html)
        self.assertIn("/demo-documents", self.javascript)
        self.assertIn('input.type = "file"', self.javascript)
        self.assertIn("uploadDocument(", self.javascript)
        self.assertIn("Submit Application", self.html)

    def test_document_uploads_are_immediately_available_with_mobile_camera(self):
        self.assertNotIn('id="start-documents-btn"', self.html)
        self.assertNotIn("startDocumentCollection", self.javascript)
        self.assertIn('applicationState.status === "IN_PROGRESS"', self.javascript)
        self.assertIn('cameraInput.accept = "image/*"', self.javascript)
        self.assertIn('cameraInput.setAttribute("capture", "environment")', self.javascript)
        self.assertIn('cameraButton.textContent = "Take photo of document"', self.javascript)
        self.assertIn(".camera-option { display: none", self.html)
        self.assertIn(".camera-option { display: inline-flex", self.html)

    def test_mobile_header_has_customer_selection_back_link(self):
        self.assertIn('class="mobile-back" href="/"', self.html)
        self.assertIn("Back to customer selection", self.html)

    def test_guided_tutorial_can_be_skipped_and_restarted(self):
        self.assertIn('id="tutorial-overlay"', self.html)
        self.assertIn('id="tutorial-skip"', self.html)
        self.assertIn('id="tutorial-back"', self.html)
        self.assertIn('id="tutorial-next"', self.html)
        self.assertGreaterEqual(self.html.count("tutorial-launch"), 2)
        self.assertIn("TUTORIAL_STEPS", self.javascript)
        self.assertIn("startTutorial", self.javascript)
        self.assertIn("finishTutorial", self.javascript)
        self.assertIn("localStorage.setItem(TUTORIAL_KEY", self.javascript)
        self.assertIn("activateWorkspaceTab(step.tab)", self.javascript)

    def test_desktop_operational_tabs_are_narrower_and_review_heading_is_blue(self):
        self.assertIn("width: min(100%,500px)", self.html)
        self.assertIn("#review-dialog .review-header h2", self.html)
        self.assertIn("color: #08285a", self.html)

    def test_inactivity_reset_is_explained_and_warned_in_a_modal(self):
        self.assertNotIn('id="reset-application-btn"', self.html)
        self.assertIn('id="inactivity-dialog"', self.html)
        self.assertIn('id="inactivity-countdown"', self.html)
        self.assertIn("/activity", self.javascript)
        self.assertIn("240_000", self.javascript)
        self.assertIn("300_000", self.javascript)
        self.assertIn("five minutes without activity", self.javascript)
        self.assertNotIn("This demo application was reset after five minutes", self.javascript)
        self.assertNotIn('id="application-status"', self.html)

    def test_header_and_benefits_use_visible_navigation_and_icons(self):
        self.assertIn("Back to customer selection", self.html)
        self.assertNotIn("Save &amp; Exit", self.html)
        self.assertIn(".brand-name { color: #082e65", self.html)
        self.assertEqual(self.html.count('class="benefit-icon"'), 3)
        self.assertGreaterEqual(self.html.count("<svg"), 3)

    def test_chat_uses_external_stage_progress_instead_of_completion_bar(self):
        self.assertNotIn('id="completion-track"', self.html)
        self.assertNotIn('id="completion-bar"', self.html)
        for stage in ("information", "documents", "credit", "submission"):
            self.assertIn(f'id="stage-{stage}"', self.html)
        self.assertIn("renderProgressRail", self.javascript)

    def test_application_shell_avoids_mixed_cached_frontend_versions(self):
        self.assertNotIn('byId("reset-application-btn")', self.javascript)
        self.assertIn("location /application/", self.nginx_config)
        self.assertIn("no-store, no-cache, must-revalidate", self.nginx_config)


if __name__ == "__main__":
    unittest.main()
