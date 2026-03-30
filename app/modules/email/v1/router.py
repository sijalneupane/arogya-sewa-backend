import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.configuration.mailgun_config import get_mailgun_service
from app.modules.email.v1.mailgun_service import MailgunGateway
from app.modules.email.v1.schemas import MailgunWebhookResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/email", tags=["Email"])


def _extract_signature_and_event(
    payload: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    signature = payload.get("signature") or {}
    event_data = payload.get("event-data") or {}
    if signature and event_data:
        return signature, event_data

    # Fallback for older webhook payload style.
    timestamp = payload.get("timestamp")
    token = payload.get("token")
    webhook_signature = payload.get("signature")
    event = payload.get("event")
    recipient = payload.get("recipient")

    if timestamp and token and webhook_signature:
        signature = {
            "timestamp": str(timestamp),
            "token": str(token),
            "signature": str(webhook_signature),
        }
        event_data = {"event": event, "recipient": recipient}

    return signature, event_data


@router.post("/mailgun/webhooks/events", response_model=MailgunWebhookResponse)
async def handle_mailgun_webhook(
    request: Request,
    service: MailgunGateway = Depends(get_mailgun_service),
):
    payload: dict[str, Any]
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        payload = await request.json()
    else:
        form = await request.form()
        payload = dict(form)
        event_data = payload.get("event-data")
        if isinstance(event_data, str):
            try:
                payload["event-data"] = json.loads(event_data)
            except json.JSONDecodeError:
                payload["event-data"] = {}

    signature, event_data = _extract_signature_and_event(payload)

    timestamp = str(signature.get("timestamp", ""))
    token = str(signature.get("token", ""))
    webhook_signature = str(signature.get("signature", ""))

    if not all([timestamp, token, webhook_signature]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing signature"
        )

    if not await service.verify_webhook_signature(
        timestamp=timestamp,
        token=token,
        signature=webhook_signature,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature"
        )

    event_type = event_data.get("event")
    recipient = event_data.get("recipient")

    if event_type == "failed":
        reason = event_data.get("delivery-status", {}).get("description")
        logger.warning("Mail delivery failed for %s: %s", recipient, reason)
    elif event_type == "opened":
        logger.info("Mail opened by %s", recipient)
    else:
        logger.info("Mailgun webhook event=%s recipient=%s", event_type, recipient)

    return MailgunWebhookResponse(status="accepted")
