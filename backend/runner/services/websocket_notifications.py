"""Utility helpers for broadcasting checker results over websockets."""

from __future__ import annotations

import logging
from typing import Iterable, Mapping, Optional

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

_GROUP_PATTERN = "submission_{submission_id}"
_CONTEST_GROUP_PATTERN = "contest_{contest_id}_user_{user_id}"


def broadcast_metric_update(submission_id: Optional[int], metric_name: str, metric_score: float) -> None:
    """Send a metric update to every websocket subscribed for the submission."""
    if not submission_id:
        logger.debug("Skip websocket broadcast: submission id is missing")
        return

    channel_layer = get_channel_layer()
    if channel_layer is None:
        logger.debug("Skip websocket broadcast: channel layer is not configured")
        return

    payload = {
        "type": "submission.metric",
        "submission_id": submission_id,
        "metric_name": metric_name,
        "metric_score": metric_score,
    }

    async_to_sync(channel_layer.group_send)(
        _GROUP_PATTERN.format(submission_id=submission_id),
        payload,
    )


def broadcast_contest_notification(
    contest_id: Optional[int],
    user_ids: Iterable[int],
    notification_payload: Mapping[str, object],
    *,
    unread_count_by_user: Optional[Mapping[int, int]] = None,
) -> None:
    """Send a contest notification to selected users."""
    if not contest_id:
        logger.debug("Skip contest notification broadcast: contest id is missing")
        return

    normalized_user_ids = set()
    for raw_user_id in user_ids:
        try:
            user_id = int(raw_user_id)
        except (TypeError, ValueError):
            continue
        if user_id > 0:
            normalized_user_ids.add(user_id)
    normalized_user_ids = sorted(normalized_user_ids)
    if not normalized_user_ids:
        logger.debug("Skip contest notification broadcast: empty recipients")
        return

    channel_layer = get_channel_layer()
    if channel_layer is None:
        logger.debug("Skip contest notification broadcast: channel layer is not configured")
        return

    for user_id in normalized_user_ids:
        payload = {
            "type": "contest.notification",
            "contest_id": contest_id,
            "notification": dict(notification_payload),
        }
        if unread_count_by_user is not None:
            payload["unread_count"] = int(unread_count_by_user.get(user_id, 0))

        async_to_sync(channel_layer.group_send)(
            _CONTEST_GROUP_PATTERN.format(contest_id=contest_id, user_id=user_id),
            payload,
        )


__all__ = ["broadcast_metric_update", "broadcast_contest_notification"]
