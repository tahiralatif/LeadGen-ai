"""Email tracking - open tracking, click tracking, and reply detection."""
from datetime import datetime
from typing import Optional, Dict, List
import httpx
from ..db.connection import async_session
from ..db.models import Email, EmailStatus, Response
from sqlalchemy import select, update
import uuid
import re


class EmailTracker:
    """Track email opens, clicks, and replies."""

    def __init__(self, base_url: str = "http://69.12.84.135:8000"):
        self.base_url = base_url

    def generate_tracking_pixel(self, email_id: int) -> str:
        """Generate an HTML tracking pixel for open tracking."""
        tracking_url = f"{self.base_url}/api/track/open/{email_id}"
        return f'<img src="{tracking_url}" width="1" height="1" style="display:none;" alt="" />'

    def wrap_links(self, email_id: int, html_content: str) -> str:
        """Wrap all links in email for click tracking."""
        # Find all href links
        link_pattern = r'href=["\']([^"\']+)["\']'

        def replace_link(match):
            original_url = match.group(1)
            if original_url.startswith(('http://', 'https://')):
                tracking_url = f"{self.base_url}/api/track/click/{email_id}?url={original_url}"
                return f'href="{tracking_url}"'
            return match.group(0)

        return re.sub(link_pattern, replace_link, html_content)

    async def track_open(self, email_id: int) -> bytes:
        """Track email open event."""
        try:
            async with async_session() as db:
                # Update email status
                await db.execute(
                    update(Email)
                    .where(Email.id == email_id)
                    .values(
                        status=EmailStatus.OPENED,
                        opened_at=datetime.utcnow()
                    )
                )
                await db.commit()

            # Return 1x1 transparent GIF
            return bytes([
                0x47, 0x49, 0x46, 0x38, 0x39, 0x61, 0x01, 0x00,
                0x01, 0x00, 0x80, 0x00, 0x00, 0xff, 0xff, 0xff,
                0x00, 0x00, 0x00, 0x21, 0xf9, 0x04, 0x01, 0x00,
                0x00, 0x00, 0x00, 0x2c, 0x00, 0x00, 0x00, 0x00,
                0x01, 0x00, 0x01, 0x00, 0x00, 0x02, 0x02, 0x44,
                0x01, 0x00, 0x3b
            ])
        except Exception as e:
            print(f"Error tracking open: {e}")
            return bytes([
                0x47, 0x49, 0x46, 0x38, 0x39, 0x61, 0x01, 0x00,
                0x01, 0x00, 0x80, 0x00, 0x00, 0xff, 0xff, 0xff,
                0x00, 0x00, 0x00, 0x21, 0xf9, 0x04, 0x01, 0x00,
                0x00, 0x00, 0x00, 0x2c, 0x00, 0x00, 0x00, 0x00,
                0x01, 0x00, 0x01, 0x00, 0x00, 0x02, 0x02, 0x44,
                0x01, 0x00, 0x3b
            ])

    async def track_click(self, email_id: int, original_url: str) -> str:
        """Track link click event and return redirect URL."""
        try:
            async with async_session() as db:
                # Update email status
                await db.execute(
                    update(Email)
                    .where(Email.id == email_id)
                    .values(
                        status=EmailStatus.CLICKED,
                        clicked_at=datetime.utcnow()
                    )
                )
                await db.commit()
        except Exception as e:
            print(f"Error tracking click: {e}")

        return original_url

    async def record_send(self, email_id: int, message_id: str) -> None:
        """Record email send event."""
        async with async_session() as db:
            await db.execute(
                update(Email)
                .where(Email.id == email_id)
                .values(
                    status=EmailStatus.SENT,
                    sent_at=datetime.utcnow()
                )
            )
            await db.commit()

    async def get_email_stats(self, email_id: int) -> Dict:
        """Get tracking stats for an email."""
        async with async_session() as db:
            result = await db.execute(select(Email).where(Email.id == email_id))
            email = result.scalar_one_or_none()

            if not email:
                return {}

            return {
                "email_id": email.id,
                "status": email.status.value if email.status else "unknown",
                "sent_at": email.sent_at.isoformat() if email.sent_at else None,
                "opened_at": email.opened_at.isoformat() if email.opened_at else None,
                "clicked_at": email.clicked_at.isoformat() if email.clicked_at else None,
                "opened": email.opened_at is not None,
                "clicked": email.clicked_at is not None
            }

    async def get_campaign_stats(self, campaign_id: int) -> Dict:
        """Get aggregate stats for a campaign."""
        async with async_session() as db:
            # Get all emails in campaign
            result = await db.execute(
                select(Email).where(Email.campaign_id == campaign_id)
            )
            emails = result.scalars().all()

            total = len(emails)
            sent = sum(1 for e in emails if e.status in [EmailStatus.SENT, EmailStatus.DELIVERED, EmailStatus.OPENED, EmailStatus.CLICKED])
            opened = sum(1 for e in emails if e.opened_at is not None)
            clicked = sum(1 for e in emails if e.clicked_at is not None)
            bounced = sum(1 for e in emails if e.status == EmailStatus.BOUNCED)
            failed = sum(1 for e in emails if e.status == EmailStatus.FAILED)

            return {
                "campaign_id": campaign_id,
                "total": total,
                "sent": sent,
                "opened": opened,
                "clicked": clicked,
                "bounced": bounced,
                "failed": failed,
                "open_rate": (opened / total * 100) if total > 0 else 0,
                "click_rate": (clicked / total * 100) if total > 0 else 0,
                "bounce_rate": (bounced / total * 100) if total > 0 else 0
            }


class ReplyDetector:
    """Detect email replies via IMAP."""

    def __init__(self, imap_host: str = "imap.gmail.com", imap_port: int = 993):
        self.imap_host = imap_host
        self.imap_port = imap_port

    async def check_for_replies(self, email_address: str, password: str, since_hours: int = 24) -> List[Dict]:
        """Check for new replies to the given email address."""
        # This is a placeholder - in production, use imaplib3 for async IMAP
        # For now, return empty list
        return []

    def parse_reply(self, email_data: str) -> Dict:
        """Parse an email reply to extract intent."""
        content_lower = email_data.lower()

        # Simple intent classification - check negative first
        if any(word in content_lower for word in ['not interested', 'no thanks', 'unsubscribe', 'stop']):
            intent = 'not_interested'
        elif any(word in content_lower for word in ['schedule', 'book', 'calendar', 'available']):
            intent = 'schedule'
        elif any(word in content_lower for word in ['question', 'how', 'what', 'when', 'where']):
            intent = 'question'
        elif any(word in content_lower for word in ['interested', 'yes', 'tell me more', 'meeting', 'call']):
            intent = 'interested'
        else:
            intent = 'neutral'

        # Simple sentiment
        if any(word in content_lower for word in ['great', 'awesome', 'love', 'perfect', 'excellent']):
            sentiment = 'positive'
        elif any(word in content_lower for word in ['bad', 'hate', 'terrible', 'awful', 'worst']):
            sentiment = 'negative'
        else:
            sentiment = 'neutral'

        return {
            "intent": intent,
            "sentiment": sentiment,
            "content": email_data
        }