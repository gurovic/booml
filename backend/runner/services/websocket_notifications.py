"""Utility helpers for broadcasting checker results over websockets."""

from __future__ import annotations

import logging
from typing import Optional

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

_GROUP_PATTERN = "submission_{submission_id}"


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


def broadcast_submission_update(problem_id: Optional[int], submission_id: int, status: str, metrics: Optional[dict] = None) -> None:
    """Send a submission status update to every websocket subscribed to the problem's submission list."""
    if not problem_id:
        logger.debug("Skip websocket broadcast: problem id is missing")
        return

    channel_layer = get_channel_layer()
    if channel_layer is None:
        logger.debug("Skip websocket broadcast: channel layer is not configured")
        return

    payload = {
        "type": "submission.update",
        "submission_id": submission_id,
        "status": status,
        "metrics": metrics,
    }

    async_to_sync(channel_layer.group_send)(
        f"problem_submissions_{problem_id}",
        payload,
    )


__all__ = ["broadcast_metric_update", "broadcast_submission_update"]
