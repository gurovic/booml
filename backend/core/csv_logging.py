import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


class ErrorLevelFilter(logging.Filter):
    """Allow only error-class log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno >= logging.ERROR


class CsvErrorFileHandler(logging.Handler):
    """Append error logs to a CSV file with a stable schema."""

    header = (
        "timestamp",
        "level",
        "logger",
        "module",
        "pathname",
        "lineno",
        "message",
        "exception",
    )

    def __init__(self, filename: str, encoding: str = "utf-8") -> None:
        super().__init__()
        self.base_filename = Path(filename)
        self.encoding = encoding
        self._exception_formatter = logging.Formatter()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            row = self._build_row(record)
            self._write_row(row)
        except Exception:
            self.handleError(record)

    def _build_row(self, record: logging.LogRecord) -> Iterable[object]:
        exception_text = ""
        if record.exc_info:
            exception_text = self._exception_formatter.formatException(record.exc_info)
        elif record.exc_text:
            exception_text = record.exc_text

        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()
        return (
            timestamp,
            record.levelname,
            record.name,
            record.module,
            record.pathname,
            record.lineno,
            record.getMessage(),
            exception_text,
        )

    def _write_row(self, row: Iterable[object]) -> None:
        self.acquire()
        try:
            self.base_filename.parent.mkdir(parents=True, exist_ok=True)
            needs_header = not self.base_filename.exists() or self.base_filename.stat().st_size == 0
            with self.base_filename.open("a", newline="", encoding=self.encoding) as handle:
                writer = csv.writer(handle)
                if needs_header:
                    writer.writerow(self.header)
                writer.writerow(row)
        finally:
            self.release()
