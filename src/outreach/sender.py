"""Email sender using Brevo (Sendinblue)."""
import httpx
from typing import Dict, Any
from config.settings import BREVO_API_KEY, EMAIL_FROM, EMAIL_FROM_NAME, EMAIL_REPLY_TO


class EmailSender:
    """Send emails using Brevo API."""

    def __init__(self):
        self.api_key = BREVO_API_KEY
        self.base_url = "https://api.brevo.com/v3"
        self.headers = {
            "api-key": self.api_key,
            "accept": "application/json",
            "content-type": "application/json"
        }

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        plain_content: str = None
    ) -> Dict[str, Any]:
        """Send a single email."""
        payload = {
            "sender": {
                "name": EMAIL_FROM_NAME,
                "email": EMAIL_FROM
            },
            "to": [
                {"email": to_email}
            ],
            "subject": subject,
            "htmlContent": html_content,
            "textContent": plain_content or html_content,
            "replyTo": {
                "email": EMAIL_REPLY_TO,
                "name": EMAIL_FROM_NAME
            }
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/smtp/email",
                    json=payload,
                    headers=self.headers
                )
                response.raise_for_status()
                data = response.json()

            return {
                "success": True,
                "status_code": response.status_code,
                "message_id": data.get("messageId"),
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "status_code": None,
                "message_id": None,
                "error": str(e)
            }

    async def send_batch(
        self,
        emails: list,
        delay_seconds: int = 1
    ) -> list:
        """Send multiple emails with delay."""
        import asyncio
        results = []

        for email_data in emails:
            result = await self.send_email(
                to_email=email_data["to"],
                subject=email_data["subject"],
                html_content=email_data["body"]
            )
            results.append(result)

            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)

        return results

    async def get_account_info(self) -> Dict[str, Any]:
        """Get Brevo account information."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/account",
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            return {"error": str(e)}