import hashlib
import hmac
import json
from typing import Any, Protocol

import httpx
from fastapi import HTTPException, status


class MailgunGateway(Protocol):
    async def send_text_email(
        self, *, to: list[str], subject: str, text: str
    ) -> dict[str, Any]: ...

    async def send_html_email(
        self,
        *,
        to: list[str],
        subject: str,
        html: str,
        text_fallback: str | None = None,
    ) -> dict[str, Any]: ...

    async def send_template_email(
        self,
        *,
        to: list[str],
        subject: str,
        template: str,
        template_variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    async def verify_webhook_signature(
        self,
        *,
        timestamp: str,
        token: str,
        signature: str,
    ) -> bool: ...


class HttpxMailgunGateway:
    """HTTP client for Mailgun API calls and webhook signature verification."""

    def __init__(
        self,
        *,
        api_key: str,
        domain: str,
        base_url: str,
        from_email: str,
        webhook_signing_key: str,
        timeout_seconds: float,
    ) -> None:
        self.auth = ("api", api_key)
        self.from_email = from_email
        self.webhook_signing_key = webhook_signing_key
        self.timeout_seconds = timeout_seconds
        self.messages_url = f"{base_url.rstrip('/')}/{domain}/messages"

    async def send_text_email(
        self, *, to: list[str], subject: str, text: str
    ) -> dict[str, Any]:
        data = {
            "from": self.from_email,
            "to": to,
            "subject": subject,
            "text": text,
        }
        return await self._send_message(data)

    async def send_html_email(
        self,
        *,
        to: list[str],
        subject: str,
        html: str,
        text_fallback: str | None = None,
    ) -> dict[str, Any]:
        data: dict[str, Any] = {
            "from": self.from_email,
            "to": to,
            "subject": subject,
            "html": html,
        }
        if text_fallback:
            data["text"] = text_fallback
        return await self._send_message(data)

    async def send_template_email(
        self,
        *,
        to: list[str],
        subject: str,
        template: str,
        template_variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data: dict[str, Any] = {
            "from": self.from_email,
            "to": to,
            "subject": subject,
            "template": template,
        }
        if template_variables:
            data["h:X-Mailgun-Variables"] = json.dumps(template_variables)
        return await self._send_message(data)

    async def _send_message(self, data: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(self.messages_url, auth=self.auth, data=data)

        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Mailgun send failed: {response.text}",
            )

        return response.json()

    async def verify_webhook_signature(
        self,
        *,
        timestamp: str,
        token: str,
        signature: str,
    ) -> bool:
        digest = hmac.new(
            key=self.webhook_signing_key.encode(),
            msg=f"{timestamp}{token}".encode(),
            digestmod=hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(signature, digest)
