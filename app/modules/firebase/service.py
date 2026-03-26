from firebase_admin import messaging


def send_push(token: str, title: str, body: str, data: dict | None = None):
    message = messaging.Message(
        token=token,
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data=data or {},
    )

    return messaging.send(message)


async def send_multicast_push(
    tokens: list[str], title: str, body: str, data: dict | None = None
):
    message = messaging.MulticastMessage(
        tokens=tokens,
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data=data or {},
    )

    return await messaging.send_each_for_multicast_async(message)


def send_topic_push(topic: str, title: str, body: str, data: dict | None = None):
    message = messaging.Message(
        topic=topic,
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data=data or {},
    )

    return messaging.send(message)
