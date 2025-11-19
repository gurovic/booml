import asyncio

from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator

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
