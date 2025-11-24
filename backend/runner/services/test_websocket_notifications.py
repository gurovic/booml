from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from runner.services.websocket_notifications import broadcast_metric_update


def test_broadcast_metric_update_sends_payload():
    async_group_send = AsyncMock()
    channel_layer = SimpleNamespace(group_send=async_group_send)

    with patch(
        "runner.services.websocket_notifications.get_channel_layer",
        return_value=channel_layer,
    ):
        broadcast_metric_update(7, "accuracy", 0.91)

    async_group_send.assert_called_once()
    group_name, payload = async_group_send.call_args[0]
    assert group_name == "submission_7"
    assert payload["metric_name"] == "accuracy"
    assert payload["metric_score"] == 0.91
    assert payload["submission_id"] == 7


def test_broadcast_metric_update_ignored_without_submission_id():
    with patch(
        "runner.services.websocket_notifications.get_channel_layer",
    ) as mocked_layer:
        broadcast_metric_update(None, "accuracy", 0.91)

    mocked_layer.assert_not_called()


def test_broadcast_metric_update_ignored_without_channel_layer():
    with patch(
        "runner.services.websocket_notifications.get_channel_layer",
        return_value=None,
    ) as mocked_layer:
        broadcast_metric_update(5, "accuracy", 0.91)

    mocked_layer.assert_called_once()
