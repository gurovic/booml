import csv
import logging
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from .csv_logging import CsvErrorFileHandler


class CsvErrorFileHandlerTests(SimpleTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.log_path = Path(self.tempdir.name) / "errors.csv"
        self.handler = CsvErrorFileHandler(str(self.log_path))
        self.logger = logging.getLogger("core.test.csv_logging")
        self.logger.handlers = []
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False
        self.logger.addHandler(self.handler)
        self.addCleanup(self.logger.removeHandler, self.handler)
        self.addCleanup(self.handler.close)

    def test_writes_header_once_and_appends_errors(self) -> None:
        self.logger.error("first failure")
        self.logger.error("second failure")

        with self.log_path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.reader(handle))

        self.assertEqual(
            rows[0],
            ["timestamp", "level", "logger", "module", "pathname", "lineno", "message", "exception"],
        )
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[1][1], "ERROR")
        self.assertEqual(rows[1][6], "first failure")
        self.assertEqual(rows[2][6], "second failure")

    def test_warning_is_ignored_by_attached_filter(self) -> None:
        self.handler.addFilter(lambda record: record.levelno >= logging.ERROR)

        self.logger.warning("not persisted")
        self.logger.error("persisted")

        with self.log_path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.reader(handle))

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][6], "persisted")
