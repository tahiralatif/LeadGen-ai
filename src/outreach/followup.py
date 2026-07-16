"""Follow-up email sequences."""
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from ..db.connection import async_session
from ..db.models import Email, EmailStatus, Campaign
from sqlalchemy import select, update
import httpx


class FollowUpSequence:
    """Manage follow-up email sequences."""

    def __init__(self):
        self.default_sequence = [
            {
                "step": 1,
                "delay_hours": 0,
                "subject": "Introduction: {subject}",
                "template": "Hi {first_name},\n\n{message}\n\nBest,\n{sender_name}"
            },
            {
                "step": 2,
                "delay_hours": 48,
                "subject": "Following up: {subject}",
                "template": "Hi {first_name},\n\nJust following up on my previous email. {follow_up_message}\n\nBest,\n{sender_name}"
            },
            {
                "step": 3,
                "delay_hours": 96,
                "subject": "Last chance: {subject}",
                "template": "Hi {first_name},\n\nI wanted to reach out one last time. {last_chance_message}\n\nBest,\n{sender_name}"
            }
        ]

    async def create_sequence(
        self,
        lead_id: int,
        campaign_id: int,
        subject: str,
        message: str,
        follow_up_message: str = "I wanted to make sure you saw my previous email.",
        last_chance_message: str = "If now isn't the right time, no worries. Just let me know!",
        sequence: List[Dict] = None
    ) -> List[int]:
        """Create a follow-up sequence for a lead."""
        if sequence is None:
            sequence = self.default_sequence

        email_ids = []
        now = datetime.utcnow()

        async with async_session() as db:
            for step in sequence:
                # Calculate send time
                delay = timedelta(hours=step["delay_hours"])
                send_at = now + delay

                # Create email record
                email = Email(
                    lead_id=lead_id,
                    campaign_id=campaign_id,
                    subject=subject,
                    body=message,
                    status=EmailStatus.PENDING,
                    sequence_step=step["step"],
                    created_at=send_at
                )
                db.add(email)
                await db.flush()
                email_ids.append(email.id)

            await db.commit()

        return email_ids

    async def get_pending_follow_ups(self, lead_id: int) -> List[Dict]:
        """Get pending follow-up emails for a lead."""
        async with async_session() as db:
            result = await db.execute(
                select(Email)
                .where(
                    Email.lead_id == lead_id,
                    Email.status == EmailStatus.PENDING
                )
                .order_by(Email.sequence_step)
            )
            emails = result.scalars().all()

            return [
                {
                    "email_id": email.id,
                    "step": email.sequence_step,
                    "subject": email.subject,
                    "status": email.status.value
                }
                for email in emails
            ]

    async def send_next_follow_up(
        self,
        lead_id: int,
        api_key: str,
        sender_email: str,
        sender_name: str
    ) -> Optional[Dict]:
        """Send the next pending follow-up email."""
        async with async_session() as db:
            # Get next pending email
            result = await db.execute(
                select(Email)
                .where(
                    Email.lead_id == lead_id,
                    Email.status == EmailStatus.PENDING
                )
                .order_by(Email.sequence_step)
                .limit(1)
            )
            email = result.scalar_one_or_none()

            if not email:
                return None

            # Send email via Brevo
            async with httpx.AsyncClient() as client:
                body_html = email.body.replace("\n", "<br>")
                html_content = f"""
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    {body_html}
                </body>
                </html>
                """

                response = await client.post(
                    "https://api.brevo.com/v3/smtp/email",
                    json={
                        "sender": {
                            "name": sender_name,
                            "email": sender_email
                        },
                        "to": [{"email": sender_email}],  # In production, use lead's email
                        "subject": email.subject,
                        "htmlContent": html_content,
                        "textContent": email.body
                    },
                    headers={
                        "api-key": api_key,
                        "accept": "application/json",
                        "content-type": "application/json"
                    }
                )

                if response.status_code in [200, 201]:
                    # Update email status
                    email.status = EmailStatus.SENT
                    email.sent_at = datetime.utcnow()
                    await db.commit()

                    return {
                        "email_id": email.id,
                        "step": email.sequence_step,
                        "status": "sent"
                    }
                else:
                    return {
                        "email_id": email.id,
                        "step": email.sequence_step,
                        "status": "failed",
                        "error": f"API error: {response.status_code}"
                    }

    async def cancel_sequence(self, lead_id: int, campaign_id: int) -> bool:
        """Cancel all pending follow-ups for a lead in a campaign."""
        async with async_session() as db:
            await db.execute(
                update(Email)
                .where(
                    Email.lead_id == lead_id,
                    Email.campaign_id == campaign_id,
                    Email.status == EmailStatus.PENDING
                )
                .values(status=EmailStatus.FAILED)
            )
            await db.commit()
            return True

    async def get_sequence_stats(self, lead_id: int, campaign_id: int) -> Dict:
        """Get stats for a follow-up sequence."""
        async with async_session() as db:
            result = await db.execute(
                select(Email)
                .where(
                    Email.lead_id == lead_id,
                    Email.campaign_id == campaign_id
                )
                .order_by(Email.sequence_step)
            )
            emails = result.scalars().all()

            steps = []
            for email in emails:
                steps.append({
                    "step": email.sequence_step,
                    "status": email.status.value if email.status else "unknown",
                    "sent_at": email.sent_at.isoformat() if email.sent_at else None,
                    "opened_at": email.opened_at.isoformat() if email.opened_at else None
                })

            return {
                "lead_id": lead_id,
                "campaign_id": campaign_id,
                "total_steps": len(steps),
                "steps": steps
            }