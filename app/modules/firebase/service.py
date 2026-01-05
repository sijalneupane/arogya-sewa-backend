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
