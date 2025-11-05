import json
import tempfile
import textwrap
from pathlib import Path

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..services import executor


class RunCodeArtifactsTests(TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.media_root = Path(self.tmpdir.name)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_run_python_collects_written_files(self):
        run_id = "test-run"
        code = textwrap.dedent(
            """
            from pathlib import Path

            Path("example.txt").write_text("data", encoding="utf-8")
            """
        )

        result = executor.run_python(code=code, media_root=self.media_root, run_id=run_id)

        artifact_names = {path.name for path in result.artifacts}

        self.assertIn("example.txt", artifact_names)
        self.assertNotIn("main.py", artifact_names)
        self.assertTrue((self.media_root / run_id / "example.txt").exists())

    def test_run_code_view_returns_artifacts_with_urls(self):
        run_id = "test-artifacts-view"
        code = textwrap.dedent(
            """
            with open("example.csv", "w", encoding="utf-8") as f:
                f.write("col1,col2\\n1,2\\n")
            """
        )

        payload = {
            "code": code,
            "lang": "python",
            "run_id": run_id,
        }

        with override_settings(MEDIA_ROOT=self.media_root):
            client = Client()
            response = client.post(
                reverse("runner:run_code"),
                data=json.dumps(payload),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["errors"], [])

        artifacts = data["artifacts"]
        self.assertEqual(len(artifacts), 1)
        artifact = artifacts[0]

        self.assertEqual(artifact["name"], "example.csv")
        self.assertTrue(artifact["url"].endswith(f"{run_id}/example.csv"))
        self.assertTrue((self.media_root / run_id / "example.csv").exists())
