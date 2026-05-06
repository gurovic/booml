from __future__ import annotations

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth import get_user_model

from ..models import Contest


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


class ContestNotificationConsumer(AsyncJsonWebsocketConsumer):
    """Streams contest notifications to a user for a specific contest."""

    contest_id: int
    user_id: int
    group_name: str

    async def connect(self) -> None:  # pragma: no cover - exercised via async tests
        raw_contest_id = (
            self.scope.get("url_route", {})
            .get("kwargs", {})
            .get("contest_id")
        )
        parsed_contest_id = self._parse_positive_int(raw_contest_id)
        if parsed_contest_id is None:
            await self.close(code=4400)
            return

        user = self.scope.get("user")
        if not user or not getattr(user, "is_authenticated", False):
            await self.close(code=4401)
            return

        has_access = await self._user_has_access_to_contest(user.id, parsed_contest_id)
        if not has_access:
            await self.close(code=4403)
            return

        if self.channel_layer is None:
            await self.close(code=4500)
            return

        self.contest_id = parsed_contest_id
        self.user_id = int(user.id)
        self.group_name = f"contest_{self.contest_id}_user_{self.user_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code: int) -> None:  # pragma: no cover - tested indirectly
        if self.channel_layer is None or not hasattr(self, "group_name"):
            return
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def contest_notification(self, event):
        await self.send_json(
            {
                "contest_id": event.get("contest_id") or self.contest_id,
                "notification": event.get("notification") or {},
                "unread_count": event.get("unread_count"),
            }
        )

    @staticmethod
    def _parse_positive_int(value):
        if isinstance(value, int):
            return value if value > 0 else None

        text_value = str(value).strip()
        if text_value.isdigit():
            parsed = int(text_value)
            return parsed if parsed > 0 else None
        return None

    @database_sync_to_async
    def _user_has_access_to_contest(self, user_id: int, contest_id: int) -> bool:
        user = get_user_model().objects.filter(pk=user_id).first()
        if user is None:
            return False
        contest = (
            Contest.objects.select_related("course__section", "course__owner")
            .prefetch_related("allowed_participants")
            .filter(pk=contest_id)
            .first()
        )
        if contest is None:
            return False
        return bool(contest.is_visible_to(user))
