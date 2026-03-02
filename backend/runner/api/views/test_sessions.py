from http import HTTPStatus
from tempfile import TemporaryDirectory
import importlib.util

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from runner.models import Notebook
from runner.services import vm_agent, vm_manager
from runner.services.runtime import _sessions, create_session, get_session, reset_execution_backend, run_code

User = get_user_model()


class NotebookSessionAPITests(TestCase):
    def setUp(self):
        self.sandbox_tmp = TemporaryDirectory()
        self.vm_tmp = TemporaryDirectory()
        reset_execution_backend()
        self.override = override_settings(
            RUNTIME_SANDBOX_ROOT=self.sandbox_tmp.name,
            RUNTIME_VM_ROOT=self.vm_tmp.name,
            RUNTIME_VM_BACKEND="local",
        )
        self.override.enable()
        vm_manager.reset_vm_manager()
        vm_agent.reset_vm_agents()
        self.user = User.objects.create_user(username="owner", password="pass123")
        self.client.login(username="owner", password="pass123")
        self.notebook = Notebook.objects.create(owner=self.user, title="My NB")
        self.create_url = reverse("notebook-session-create")
        self.reset_url = reverse("session-reset")
        self.stop_url = reverse("session-stop")
        self.files_url = reverse("session-files")
        self.download_url = reverse("session-file-download")
        self.upload_url = reverse("session-file-upload")
        self.preview_url = reverse("session-file-preview")
        self.chart_url = reverse("session-file-chart")
        _sessions.clear()

    def tearDown(self):
        reset_execution_backend()
        vm_manager.reset_vm_manager()
        vm_agent.reset_vm_agents()
        _sessions.clear()
        self.override.disable()
        self.sandbox_tmp.cleanup()
        self.vm_tmp.cleanup()

    def test_create_session_success(self):
        resp = self.client.post(self.create_url, {"notebook_id": self.notebook.id})
        self.assertEqual(resp.status_code, HTTPStatus.CREATED)
        data = resp.json()
        session_id = data["session_id"]
        self.assertTrue(session_id.endswith(str(self.notebook.id)))
        self.assertEqual(data["status"], "created")
        self.assertIn(session_id, _sessions)
        self.assertIn("vm", data)
        self.assertEqual(data["vm"]["id"], f"runner-{session_id.replace(':', '_')}")

    def test_create_session_forbidden_for_other_user(self):
        another = User.objects.create_user(username="other", password="pass456")
        other_nb = Notebook.objects.create(owner=another, title="Other NB")

        resp = self.client.post(self.create_url, {"notebook_id": other_nb.id})
        self.assertEqual(resp.status_code, HTTPStatus.FORBIDDEN)
        self.assertNotIn(f"notebook:{other_nb.id}", _sessions)

    def test_reset_session_success(self):
        session_id = f"notebook:{self.notebook.id}"
        first_session = create_session(session_id)

        resp = self.client.post(self.reset_url, {"session_id": session_id})
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = resp.json()
        self.assertEqual(data["session_id"], session_id)
        self.assertEqual(data["status"], "reset")
        self.assertIn("vm", data)

        second_session = get_session(session_id, touch=False)
        self.assertIsNotNone(second_session)
        self.assertIsNot(first_session, second_session)

    def test_reset_session_forbidden_for_other_user(self):
        another = User.objects.create_user(username="other2", password="pass789")
        other_nb = Notebook.objects.create(owner=another, title="Other NB")
        session_id = f"notebook:{other_nb.id}"
        create_session(session_id)

        resp = self.client.post(self.reset_url, {"session_id": session_id})

        self.assertEqual(resp.status_code, HTTPStatus.FORBIDDEN)
        # ensure session not reset: still same object
        original = get_session(session_id, touch=False)
        again = get_session(session_id, touch=False)
        self.assertIs(original, again)

    def test_reset_session_missing_returns_404(self):
        session_id = f"notebook:{self.notebook.id}"
        resp = self.client.post(self.reset_url, {"session_id": session_id})
        self.assertEqual(resp.status_code, HTTPStatus.NOT_FOUND)

    def test_session_files_listing(self):
        session_id = f"notebook:{self.notebook.id}"
        create_session(session_id)
        run_code(session_id, "open('result.txt','w').write('hello')")

        resp = self.client.get(f"{self.files_url}?session_id={session_id}")
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = resp.json()
        self.assertTrue(any(item["path"] == "result.txt" for item in data.get("files", [])))
        self.assertIn("vm", data)

    def test_session_files_listing_hides_streams(self):
        session_id = f"notebook:{self.notebook.id}"
        session = create_session(session_id)
        stream_dir = session.workdir / ".streams"
        stream_dir.mkdir(parents=True, exist_ok=True)
        (stream_dir / "tmp.stdout").write_text("x", encoding="utf-8")

        resp = self.client.get(f"{self.files_url}?session_id={session_id}")

        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = resp.json()
        paths = {item["path"] for item in data.get("files", [])}
        self.assertNotIn(".streams/tmp.stdout", paths)

    def test_session_file_download(self):
        session_id = f"notebook:{self.notebook.id}"
        create_session(session_id)
        run_code(session_id, "open('download.txt','w').write('ping')")

        resp = self.client.get(f"{self.download_url}?session_id={session_id}&path=download.txt")
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        content = b"".join(resp.streaming_content)
        self.assertEqual(content, b"ping")

    def test_session_file_download_prevents_escape(self):
        session_id = f"notebook:{self.notebook.id}"
        create_session(session_id)

        resp = self.client.get(f"{self.download_url}?session_id={session_id}&path=../secret.txt")
        self.assertEqual(resp.status_code, HTTPStatus.NOT_FOUND)

    def test_session_file_delete_success(self):
        session_id = f"notebook:{self.notebook.id}"
        session = create_session(session_id)
        target = session.workdir / "delete_me.txt"
        target.write_text("bye", encoding="utf-8")

        resp = self.client.delete(
            self.download_url,
            data={"session_id": session_id, "path": "delete_me.txt"},
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = resp.json()
        self.assertEqual(data["session_id"], session_id)
        self.assertEqual(data["path"], "delete_me.txt")
        self.assertTrue(data["deleted"])
        self.assertFalse(target.exists())

    def test_session_file_delete_prevents_escape(self):
        session_id = f"notebook:{self.notebook.id}"
        create_session(session_id)

        resp = self.client.delete(
            self.download_url,
            data={"session_id": session_id, "path": "../secret.txt"},
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, HTTPStatus.NOT_FOUND)

    def test_session_file_delete_forbidden_for_other_user(self):
        session_id = f"notebook:{self.notebook.id}"
        session = create_session(session_id)
        target = session.workdir / "private.txt"
        target.write_text("secret", encoding="utf-8")

        other = User.objects.create_user(username="other_deleter", password="pass123")
        self.client.logout()
        self.client.login(username="other_deleter", password="pass123")

        resp = self.client.delete(
            self.download_url,
            data={"session_id": session_id, "path": "private.txt"},
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, HTTPStatus.FORBIDDEN)
        self.assertTrue(target.exists())

    def test_session_file_delete_missing_file_returns_404(self):
        session_id = f"notebook:{self.notebook.id}"
        create_session(session_id)

        resp = self.client.delete(
            self.download_url,
            data={"session_id": session_id, "path": "missing.txt"},
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, HTTPStatus.NOT_FOUND)

    def test_session_file_delete_missing_session_returns_404(self):
        session_id = f"notebook:{self.notebook.id}"

        resp = self.client.delete(
            self.download_url,
            data={"session_id": session_id, "path": "file.txt"},
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, HTTPStatus.NOT_FOUND)

    def test_session_file_upload(self):
        session_id = f"notebook:{self.notebook.id}"
        session = create_session(session_id)
        payload = {
            "session_id": session_id,
            "file": SimpleUploadedFile("train.csv", b"col1\n1\n2\n", content_type="text/csv"),
        }

        resp = self.client.post(self.upload_url, payload)

        self.assertEqual(resp.status_code, HTTPStatus.CREATED)
        data = resp.json()
        self.assertEqual(data["session_id"], session_id)
        self.assertEqual(data["path"], "train.csv")
        uploaded = session.workdir / "train.csv"
        self.assertTrue(uploaded.exists())
        with uploaded.open("rb") as fh:
            self.assertEqual(fh.read(), b"col1\n1\n2\n")

    def test_session_file_upload_nested_path(self):
        session_id = f"notebook:{self.notebook.id}"
        session = create_session(session_id)

        resp = self.client.post(
            self.upload_url,
            {
                "session_id": session_id,
                "path": "datasets/",
                "file": SimpleUploadedFile("data.txt", b"abc"),
            },
        )

        self.assertEqual(resp.status_code, HTTPStatus.CREATED)
        data = resp.json()
        self.assertEqual(data["path"], "datasets/data.txt")
        uploaded = session.workdir / "datasets" / "data.txt"
        self.assertTrue(uploaded.exists())
        with uploaded.open("rb") as fh:
            self.assertEqual(fh.read(), b"abc")

    def test_session_file_upload_prevents_escape(self):
        session_id = f"notebook:{self.notebook.id}"
        create_session(session_id)

        resp = self.client.post(
            self.upload_url,
            {
                "session_id": session_id,
                "path": "../outside.txt",
                "file": SimpleUploadedFile("outside.txt", b"nope"),
            },
        )

        self.assertEqual(resp.status_code, HTTPStatus.NOT_FOUND)

    def test_session_file_upload_missing_session_returns_404(self):
        session_id = f"notebook:{self.notebook.id}"

        resp = self.client.post(
            self.upload_url,
            {
                "session_id": session_id,
                "file": SimpleUploadedFile("file.txt", b"data"),
            },
        )

        self.assertEqual(resp.status_code, HTTPStatus.NOT_FOUND)

    def test_session_file_preview_csv(self):
        session_id = f"notebook:{self.notebook.id}"
        session = create_session(session_id)
        csv_path = session.workdir / "sample.csv"
        csv_path.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")

        resp = self.client.get(f"{self.preview_url}?session_id={session_id}&path=sample.csv")

        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = resp.json()
        self.assertEqual(data["format"], "csv")
        self.assertEqual(data["columns"], ["a", "b"])
        self.assertEqual(data["rows"][0], ["1", "2"])

    def test_session_file_preview_prevents_escape(self):
        session_id = f"notebook:{self.notebook.id}"
        create_session(session_id)

        resp = self.client.get(f"{self.preview_url}?session_id={session_id}&path=../secret.csv")

        self.assertEqual(resp.status_code, HTTPStatus.NOT_FOUND)

    def test_session_file_preview_unsupported_type(self):
        session_id = f"notebook:{self.notebook.id}"
        session = create_session(session_id)
        txt_path = session.workdir / "notes.txt"
        txt_path.write_text("hello", encoding="utf-8")

        resp = self.client.get(f"{self.preview_url}?session_id={session_id}&path=notes.txt")

        self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)
        self.assertIn("Unsupported file type", resp.json().get("detail", ""))

    def test_session_file_preview_forbidden_for_other_user(self):
        session_id = f"notebook:{self.notebook.id}"
        session = create_session(session_id)
        csv_path = session.workdir / "sample.csv"
        csv_path.write_text("a,b\n1,2\n", encoding="utf-8")

        other = User.objects.create_user(username="other_viewer", password="pass123")
        self.client.logout()
        self.client.login(username="other_viewer", password="pass123")

        resp = self.client.get(f"{self.preview_url}?session_id={session_id}&path=sample.csv")

        self.assertEqual(resp.status_code, HTTPStatus.FORBIDDEN)

    def test_session_file_preview_missing_session_returns_404(self):
        session_id = f"notebook:{self.notebook.id}"

        resp = self.client.get(f"{self.preview_url}?session_id={session_id}&path=sample.csv")

        self.assertEqual(resp.status_code, HTTPStatus.NOT_FOUND)

    def test_session_file_chart_schema_and_recommendation(self):
        session_id = f"notebook:{self.notebook.id}"
        session = create_session(session_id)
        csv_path = session.workdir / "sample.csv"
        csv_path.write_text("x,y,cat\n1,10,a\n2,11,b\n3,12,a\n", encoding="utf-8")

        resp = self.client.post(
            self.chart_url,
            {"session_id": session_id, "path": "sample.csv"},
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = resp.json()
        self.assertIn("schema", data)
        self.assertEqual(data["schema"]["numeric_columns"], ["x", "y"])
        self.assertIsNotNone(data.get("recommended"))
        self.assertEqual(data["recommended"]["chart_type"], "scatter")

    def test_session_file_chart_bar_with_aggregation(self):
        session_id = f"notebook:{self.notebook.id}"
        session = create_session(session_id)
        csv_path = session.workdir / "scores.csv"
        csv_path.write_text(
            "city,score,attempts\nMoscow,10,1\nMoscow,20,2\nSPB,5,3\n",
            encoding="utf-8",
        )

        resp = self.client.post(
            self.chart_url,
            {
                "session_id": session_id,
                "path": "scores.csv",
                "chart_type": "bar",
                "x": "city",
                "y": ["score"],
                "agg": "mean",
            },
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = resp.json()
        chart = data.get("chart") or {}
        self.assertEqual(chart.get("type"), "bar")
        self.assertTrue((data.get("chart_image") or "").startswith("data:image/png;base64,"))
        series = chart.get("series") or []
        self.assertTrue(series)
        values = {item["x"]: item["y"] for item in series[0]["points"]}
        self.assertEqual(values["Moscow"], 15.0)
        self.assertEqual(values["SPB"], 5.0)

    def test_session_file_chart_hist(self):
        session_id = f"notebook:{self.notebook.id}"
        session = create_session(session_id)
        csv_path = session.workdir / "hist.csv"
        csv_path.write_text("score\n1\n2\n3\n4\n5\n", encoding="utf-8")

        resp = self.client.post(
            self.chart_url,
            {
                "session_id": session_id,
                "path": "hist.csv",
                "chart_type": "hist",
                "y": ["score"],
                "bins": 4,
            },
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = resp.json()
        chart = data.get("chart") or {}
        self.assertEqual(chart.get("type"), "hist")
        self.assertTrue((data.get("chart_image") or "").startswith("data:image/png;base64,"))
        bins = (chart.get("series") or [{}])[0].get("bins") or []
        self.assertEqual(len(bins), 4)
        self.assertEqual(sum(item["count"] for item in bins), 5)

    def test_session_file_chart_forbidden_for_other_user(self):
        session_id = f"notebook:{self.notebook.id}"
        session = create_session(session_id)
        csv_path = session.workdir / "sample.csv"
        csv_path.write_text("x,y\n1,2\n", encoding="utf-8")

        other = User.objects.create_user(username="chart_other", password="pass123")
        self.client.logout()
        self.client.login(username="chart_other", password="pass123")

        resp = self.client.post(
            self.chart_url,
            {"session_id": session_id, "path": "sample.csv"},
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, HTTPStatus.FORBIDDEN)

    def test_session_file_preview_parquet(self):
        session_id = f"notebook:{self.notebook.id}"
        session = create_session(session_id)
        parquet_path = session.workdir / "sample.parquet"

        has_pyarrow = importlib.util.find_spec("pyarrow") is not None
        if has_pyarrow:
            import pyarrow as pa
            import pyarrow.parquet as pq

            table = pa.table({"a": [1, 2], "b": ["x", "y"]})
            pq.write_table(table, parquet_path)
        else:
            # Simulate a parquet upload in environments without pyarrow.
            parquet_path.write_bytes(b"PAR1")

        resp = self.client.get(f"{self.preview_url}?session_id={session_id}&path=sample.parquet")
        data = resp.json()
        if has_pyarrow:
            self.assertEqual(resp.status_code, HTTPStatus.OK)
            self.assertEqual(data["format"], "parquet")
            self.assertEqual(data["columns"], ["a", "b"])
            self.assertEqual(data["rows"][0], ["1", "x"])
        else:
            self.assertEqual(resp.status_code, HTTPStatus.BAD_REQUEST)
            self.assertIn("pyarrow", (data.get("detail") or "").lower())

    def test_stop_session_success(self):
        session_id = f"notebook:{self.notebook.id}"
        create_session(session_id)

        resp = self.client.post(self.stop_url, {"session_id": session_id})

        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertEqual(resp.json()["status"], "stopped")
        self.assertIsNone(get_session(session_id, touch=False))

    def test_stop_session_not_found(self):
        session_id = f"notebook:{self.notebook.id}"
        resp = self.client.post(self.stop_url, {"session_id": session_id})
        self.assertEqual(resp.status_code, HTTPStatus.NOT_FOUND)

    def test_session_files_missing_session_returns_404(self):
        session_id = f"notebook:{self.notebook.id}"
        resp = self.client.get(f"{self.files_url}?session_id={session_id}")
        self.assertEqual(resp.status_code, HTTPStatus.NOT_FOUND)
