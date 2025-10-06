import json
from pathlib import Path
from pydantic import BaseModel, Field, ValidationError
from django.utils import timezone
from runner.models import Submission

class ReportSchema(BaseModel):
    status: str = Field(..., description="Статус выполнения ('success', 'failed', ...)")
    score_primary: float | None = Field(None, description="Основная метрика (accuracy, etc.)")
    score_extra: dict | None = Field(default_factory=dict, description="Дополнительные метрики")
    logs: str | list | None = Field(default=None, description="Логи или результат выполнения")

class ReportParser:
    def __init__(self, submission_id: int, report_path: str):
        self.submission_id = submission_id
        self.report_path = Path(report_path)

    def parse_and_update(self) -> Submission:
        try:
            content = self.report_path.read_text(encoding="utf-8")
            parsed = ReportSchema.model_validate_json(content)
        except (FileNotFoundError, ValidationError, json.JSONDecodeError) as e:
            submission = Submission.objects.get(id=self.submission_id)
            submission.status = "failed"
            submission.output = f"Report parsing error: {e}"
            submission.save(update_fields=["status", "output"])
            return submission

        submission = Submission.objects.get(id=self.submission_id)
        submission.status = parsed.status
        submission.score_primary = parsed.score_primary
        submission.score_extra = parsed.score_extra or {}
        submission.output = parsed.logs if isinstance(parsed.logs, str) else json.dumps(parsed.logs)
        submission.save(update_fields=["status", "score_primary", "score_extra", "output"])
        return submission
