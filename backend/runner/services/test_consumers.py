import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from channels.layers import get_channel_layer
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.urls import re_path

from runner.services import consumers
from core.asgi import application


def test_submission_consumer_receives_metric_event():
    async def scenario():
        communicator = WebsocketCommunicator(application, "/ws/submissions/42/")
        connected, _ = await communicator.connect()
        assert connected

        channel_layer = get_channel_layer()
        assert channel_layer is not None

        await channel_layer.group_send(
            "submission_42",
            {
                "type": "submission.metric",
                "metric_name": "accuracy",
                "metric_score": 0.88,
            },
        )

        response = await communicator.receive_json_from(timeout=10)
        assert response == {
            "submission_id": 42,
            "metric_name": "accuracy",
            "metric_score": 0.88,
        }

        await communicator.disconnect()

    asyncio.run(scenario())


def test_contest_consumer_receives_notification_event():
    async def scenario():
        contest_application = URLRouter(
            [
                re_path(
                    r"^ws/contests/(?P<contest_id>\d+)/notifications/$",
                    consumers.ContestNotificationConsumer.as_asgi(),
                )
            ]
        )
        with patch.object(
            consumers.ContestNotificationConsumer,
            "_user_has_access_to_contest",
            new=AsyncMock(return_value=True),
        ):
            communicator = WebsocketCommunicator(contest_application, "/ws/contests/55/notifications/")
            communicator.scope["user"] = SimpleNamespace(id=9, is_authenticated=True)

            connected, _ = await communicator.connect()
            assert connected

            channel_layer = get_channel_layer()
            assert channel_layer is not None

            await channel_layer.group_send(
                "contest_55_user_9",
                {
                    "type": "contest.notification",
                    "contest_id": 55,
                    "notification": {
                        "id": 1001,
                        "kind": "announcement",
                        "text": "Внимание: обновлён дедлайн",
                    },
                    "unread_count": 2,
                },
            )

            response = await communicator.receive_json_from(timeout=10)
            assert response["contest_id"] == 55
            assert response["notification"]["id"] == 1001
            assert response["notification"]["kind"] == "announcement"
            assert response["unread_count"] == 2

            await communicator.disconnect()

    asyncio.run(scenario())
