from types import SimpleNamespace
from django.template.loader import render_to_string
from django.test import TestCase


class SubmissionDetailTemplateTests(TestCase):
    def test_template_includes_websocket_client_and_submission_id(self):
        submission = SimpleNamespace(
            id=123,
            problem=SimpleNamespace(title="Some Problem"),
            created_at=None,
            get_status_display="OK",
            metric=0.5,
            file=None,
        )

        rendered = render_to_string("runner/submissions/detail.html", {"submission": submission})

        # It should include the JSON script with the submission-id
        self.assertIn('id="submission-id"', rendered)

        # The websocket path string '/ws/submissions/' should be present (full URL built in JS at runtime)
        self.assertIn('/ws/submissions/', rendered)

        # Metric span element for updating via JS should exist
        self.assertIn('id="submission-metric"', rendered)

        # The template should include an inline WebSocket constructor
        self.assertIn('new WebSocket', rendered)
