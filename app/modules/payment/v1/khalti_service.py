import httpx
from typing import Optional, Protocol

from app.core.configuration.khalti_config import KhaltiConfig


class KhaltiGatewayError(Exception):
    """Raised when Khalti gateway returns an unexpected response."""


class KhaltiGateway(Protocol):
    async def initiate_payment(
        self,
        amount: int,
        purchase_order_id: str,
        purchase_order_name: str,
        customer_name: str,
        customer_email: str,
        customer_phone: str,
        return_url: str,
        website_url: str,
        merchant_extra: Optional[str] = None,
    ) -> dict: ...

    async def verify_payment(self, pidx: str) -> dict: ...


class HttpxKhaltiGateway:
    """HTTP client for Khalti Payment Gateway API calls."""

    def __init__(
        self,
        api_url: str,
        secret_key: str,
        timeout: float = 30.0,
    ) -> None:
        self.api_url = api_url
        self.secret_key = secret_key
        self.timeout = timeout

    def _get_headers(self) -> dict:
        """Get headers with Khalti authorization"""
        return {
            "Authorization": f"Key {self.secret_key}",
            "Content-Type": "application/json",
        }

    async def initiate_payment(
        self,
        amount: int,
        purchase_order_id: str,
        purchase_order_name: str,
        customer_name: str,
        customer_email: str,
        customer_phone: str,
        return_url: str,
        website_url: str,
        merchant_extra: Optional[str] = None,
    ) -> dict:
        """
        Initiate payment request with Khalti.

        Args:
            amount: Amount in paisa (e.g., 100000 for Rs. 1000)
            purchase_order_id: Unique order ID from merchant
            purchase_order_name: Name/description of purchase
            customer_name: Customer name
            customer_email: Customer email
            customer_phone: Customer phone (Khalti ID)
            return_url: URL to return after payment
            website_url: Merchant website URL
            merchant_extra: Optional extra merchant data

        Returns:
            Dictionary with pidx, payment_url, expires_at, expires_in
        """
        payload = {
            "return_url": return_url,
            "website_url": website_url,
            "amount": amount,
            "purchase_order_id": purchase_order_id,
            "purchase_order_name": purchase_order_name,
            "customer_info": {
                "name": customer_name,
                "email": customer_email,
                "phone": customer_phone,
            },
            "merchant_extra": merchant_extra,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/epayment/initiate/",
                json=payload,
                headers=self._get_headers(),
                timeout=self.timeout,
            )

        if response.status_code != 200:
            raise KhaltiGatewayError(
                f"Khalti API error: {response.status_code} - {response.text}"
            )

        return response.json()

    async def verify_payment(self, pidx: str) -> dict:
        """
        Verify payment status using pidx from Khalti.

        Args:
            pidx: Payment identifier from Khalti initiation

        Returns:
            Dictionary with payment status, amount, transaction_id, etc.
        """
        payload = {"pidx": pidx}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/epayment/lookup/",
                json=payload,
                headers=self._get_headers(),
                timeout=self.timeout,
            )

        if response.status_code not in [200, 400]:
            raise KhaltiGatewayError(
                f"Khalti API error: {response.status_code} - {response.text}"
            )

        return response.json()


def get_khalti_gateway() -> KhaltiGateway:
    """Dependency provider for Khalti gateway client."""
    return HttpxKhaltiGateway(
        api_url=KhaltiConfig.API_URL,
        secret_key=KhaltiConfig.SECRET_KEY,
    )
