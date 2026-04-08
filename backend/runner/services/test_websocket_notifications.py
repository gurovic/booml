from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from runner.services.websocket_notifications import (
    broadcast_contest_notification,
    broadcast_metric_update,
)


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


def test_broadcast_contest_notification_sends_to_each_recipient():
    async_group_send = AsyncMock()
    channel_layer = SimpleNamespace(group_send=async_group_send)

    with patch(
        "runner.services.websocket_notifications.get_channel_layer",
        return_value=channel_layer,
    ):
        broadcast_contest_notification(
            contest_id=17,
            user_ids=[11, 12],
            notification_payload={"id": 101, "kind": "announcement"},
            unread_count_by_user={11: 3, 12: 1},
        )

    assert async_group_send.call_count == 2
    first_group, first_payload = async_group_send.call_args_list[0].args
    second_group, second_payload = async_group_send.call_args_list[1].args
    assert first_group == "contest_17_user_11"
    assert second_group == "contest_17_user_12"
    assert first_payload["type"] == "contest.notification"
    assert second_payload["type"] == "contest.notification"
    assert first_payload["notification"]["id"] == 101
    assert first_payload["unread_count"] == 3
    assert second_payload["unread_count"] == 1


def test_broadcast_contest_notification_ignored_without_valid_recipients():
    with patch(
        "runner.services.websocket_notifications.get_channel_layer",
    ) as mocked_layer:
        broadcast_contest_notification(
            contest_id=4,
            user_ids=["x", None, -1],
            notification_payload={"id": 1},
        )

    mocked_layer.assert_not_called()
