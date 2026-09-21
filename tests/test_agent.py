import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from google.genai import types as genai_types

from backend import application
from backend.agent import (
    AGENT_INSTRUCTION,
    get_application_state,
    root_agent,
    save_application_section,
)
from backend.main import app


class _FakeSessionService:
    def __init__(self):
        self.session = None

    async def get_session(self, **kwargs):
        return self.session

    async def create_session(self, **kwargs):
        self.session = {"session_id": kwargs["session_id"]}
        return self.session


class _FakeEvent:
    def __init__(self, text):
        self.content = genai_types.Content(
            role="model",
            parts=[genai_types.Part(text=text)],
        )

    def is_final_response(self):
        return True


class _FakeRunner:
    def __init__(self):
        self.session_service = _FakeSessionService()
        self.received_text = None

    async def run_async(self, **kwargs):
        self.received_text = kwargs["new_message"].parts[0].text
        yield _FakeEvent("What is your first name?")


class AgentTests(unittest.TestCase):
    def setUp(self):
        application._APPLICATIONS.clear()

    def tearDown(self):
        application._APPLICATIONS.clear()

    def test_agent_instruction_contains_decision_safety_boundaries(self):
        instruction = AGENT_INSTRUCTION.lower()
        self.assertIn("do not approve", instruction)
        self.assertIn("do not approve, decline", instruction)
        self.assertIn("not a lending decision", instruction)
        self.assertIn("backend application state is authoritative", instruction)

    def test_agent_has_no_credit_result_selection_tool(self):
        tool_names = {tool.name for tool in root_agent.tools}
        self.assertNotIn("run_simulated_credit_check", tool_names)
        self.assertNotIn("credit_check", tool_names)
        self.assertIn("save_credit_consent", tool_names)

    def test_agent_tools_write_to_authoritative_application_store(self):
        loan_application = application.create_application()
        save_application_section(
            loan_application.application_id,
            "personal",
            {"first_name": "Maya"},
        )

        state = get_application_state(loan_application.application_id)
        self.assertEqual(state["personal"]["first_name"], "Maya")
        self.assertEqual(len(application._APPLICATIONS), 1)

    def test_invalid_agent_section_returns_recoverable_error(self):
        loan_application = application.create_application()

        result = save_application_section(
            loan_application.application_id,
            "applicant_details",
            {"first_name": "Maya"},
        )

        self.assertEqual(result["status"], "error")
        self.assertIn("personal", result["allowed_sections"])
        self.assertIsNone(loan_application.personal.first_name)

    def test_chat_creates_application_and_returns_its_identity(self):
        fake_runner = _FakeRunner()
        client = TestClient(app)

        with patch("backend.main.runner", fake_runner):
            response = client.post(
                "/api/chat",
                json={
                    "session_id": "session-123",
                    "message": "I want to start an application.",
                },
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["reply"], "What is your first name?")
        self.assertTrue(body["application_id"].startswith("APP-"))
        self.assertEqual(body["status"], "IN_PROGRESS")
        self.assertIn(
            f"application_id: {body['application_id']}",
            fake_runner.received_text,
        )

    def test_chat_rejects_unknown_application_id_before_model_call(self):
        fake_runner = _FakeRunner()
        client = TestClient(app)

        with patch("backend.main.runner", fake_runner):
            response = client.post(
                "/api/chat",
                json={
                    "session_id": "session-123",
                    "application_id": "APP-2099-NOTFOUND",
                    "message": "Continue.",
                },
            )

        self.assertEqual(response.status_code, 404)
        self.assertIsNone(fake_runner.received_text)


if __name__ == "__main__":
    unittest.main()
