from __future__ import annotations

from channels.generic.websocket import AsyncJsonWebsocketConsumer


class SubmissionMetricConsumer(AsyncJsonWebsocketConsumer):
    """Streams metric updates for a single submission to connected clients."""

    group_name: str
    submission_id: int

    async def connect(self) -> None:  # pragma: no cover - exercised via async tests
        raw_submission_id = (
            self.scope.get("url_route", {})
            .get("kwargs", {})
            .get("submission_id")
        )

        if raw_submission_id is None:
            await self.close(code=4404)
            return

        parsed_submission_id = self._parse_submission_id(raw_submission_id)
        if parsed_submission_id is None:
            await self.close(code=4400)
            return

        self.submission_id = parsed_submission_id

        if self.channel_layer is None:
            await self.close(code=4500)
            return

        self.group_name = f"submission_{self.submission_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code: int) -> None:  # pragma: no cover - tested indirectly
        if self.channel_layer is None or not hasattr(self, "group_name"):
            return
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def submission_metric(self, event):
        await self.send_json(
            {
                "submission_id": self.submission_id,
                "metric_name": event.get("metric_name"),
                "metric_score": event.get("metric_score"),
            }
        )

    @staticmethod
    def _parse_submission_id(value):
        if isinstance(value, int):
            return value

        if isinstance(value, str):
            trimmed = value.strip()
            if trimmed.lstrip("-").isdigit():
                return int(trimmed)

        text_value = str(value).strip()
        if text_value.lstrip("-").isdigit():
            return int(text_value)

        return None


class ProblemSubmissionsConsumer(AsyncJsonWebsocketConsumer):
    """Streams submission status updates for all submissions of a problem to connected clients."""

    group_name: str
    problem_id: int

    async def connect(self) -> None:  # pragma: no cover - exercised via async tests
        raw_problem_id = (
            self.scope.get("url_route", {})
            .get("kwargs", {})
            .get("problem_id")
        )

        if raw_problem_id is None:
            await self.close(code=4404)
            return

        parsed_problem_id = self._parse_id(raw_problem_id)
        if parsed_problem_id is None:
            await self.close(code=4400)
            return

        self.problem_id = parsed_problem_id

        if self.channel_layer is None:
            await self.close(code=4500)
            return

        self.group_name = f"problem_submissions_{self.problem_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code: int) -> None:  # pragma: no cover - tested indirectly
        if self.channel_layer is None or not hasattr(self, "group_name"):
            return
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def submission_update(self, event):
        """Handle submission status update events."""
        await self.send_json(
            {
                "type": "submission_update",
                "submission_id": event.get("submission_id"),
                "status": event.get("status"),
                "metrics": event.get("metrics"),
            }
        )

    @staticmethod
    def _parse_id(value):
        if isinstance(value, int):
            return value

        if isinstance(value, str):
            trimmed = value.strip()
            if trimmed.lstrip("-").isdigit():
                return int(trimmed)

        text_value = str(value).strip()
        if text_value.lstrip("-").isdigit():
            return int(text_value)

        return None
