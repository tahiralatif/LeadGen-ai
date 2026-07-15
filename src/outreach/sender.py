"""Email sender using SendGrid."""
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content, Asm, GroupId
from typing import Dict, Any
from config.settings import SENDGRID_API_KEY, EMAIL_FROM, EMAIL_FROM_NAME, EMAIL_REPLY_TO


class EmailSender:
    """Send emails using SendGrid API."""

    def __init__(self):
        self.client = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        plain_content: str = None,
        unsubscribe_group_id: int = None
    ) -> Dict[str, Any]:
        """Send a single email."""
        message = Mail(
            from_email=Email(EMAIL_FROM, EMAIL_FROM_NAME),
            to_emails=To(to_email),
            subject=subject,
            html_content=Content("text/html", html_content),
            plain_text_content=Content("text/plain", plain_content or html_content)
        )

        # Add reply-to
        message.reply_to = Email(EMAIL_REPLY_TO)

        # Add unsubscribe handling
        if unsubscribe_group_id:
            message.asm = Asm(GroupId(unsubscribe_group_id))

        try:
            response = self.client.send(message)
            return {
                "success": response.status_code in [200, 201, 202],
                "status_code": response.status_code,
                "message_id": response.headers.get("X-Message-Id"),
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
                html_content=email_data["body"],
                unsubscribe_group_id=email_data.get("unsubscribe_group_id")
            )
            results.append(result)

            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)

        return results