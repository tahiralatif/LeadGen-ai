"""Campaign management for email sequences."""
from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..db.models import Campaign, Email, Lead, CampaignStatus, EmailStatus
from ..personalization.engine import PersonalizationEngine
from .sender import EmailSender


class CampaignManager:
    """Manage email campaigns and sequences."""

    def __init__(self):
        self.personalizer = PersonalizationEngine()
        self.sender = EmailSender()

    async def create_campaign(
        self,
        db: AsyncSession,
        name: str,
        subject_line: str,
        message_template: str,
        follow_up_template: str = None
    ) -> Campaign:
        """Create a new campaign."""
        campaign = Campaign(
            name=name,
            subject_line=subject_line,
            message_template=message_template,
            follow_up_template=follow_up_template or message_template,
            status=CampaignStatus.DRAFT
        )
        db.add(campaign)
        await db.commit()
        await db.refresh(campaign)
        return campaign

    async def add_leads_to_campaign(
        self,
        db: AsyncSession,
        campaign_id: int,
        lead_ids: List[int]
    ):
        """Add leads to a campaign."""
        # Update campaign total
        campaign = await db.get(Campaign, campaign_id)
        campaign.total_leads = len(lead_ids)
        await db.commit()

    async def send_initial_emails(
        self,
        db: AsyncSession,
        campaign_id: int
    ) -> Dict[str, Any]:
        """Send initial emails for a campaign."""
        campaign = await db.get(Campaign, campaign_id)
        if not campaign:
            raise ValueError("Campaign not found")

        # Get leads that haven't been emailed
        stmt = select(Lead).where(
            Lead.id.notin_(
                select(Email.lead_id).where(Email.campaign_id == campaign_id)
            )
        )
        result = await db.execute(stmt)
        leads = result.scalars().all()

        sent_count = 0
        failed_count = 0

        for lead in leads:
            # Generate personalized email
            email_content = await self.personalizer.generate_email(
                lead={
                    "first_name": lead.first_name,
                    "last_name": lead.last_name,
                    "company": lead.company,
                    "title": lead.title,
                    "location": lead.location,
                    "industry": lead.industry if hasattr(lead, "industry") else None
                },
                template=campaign.message_template
            )

            # Send email
            result = await self.sender.send_email(
                to_email=lead.email,
                subject=email_content["subject"],
                html_content=email_content["body"]
            )

            # Record email
            email = Email(
                lead_id=lead.id,
                campaign_id=campaign_id,
                subject=email_content["subject"],
                body=email_content["body"],
                status=EmailStatus.SENT if result["success"] else EmailStatus.FAILED,
                sent_at=datetime.utcnow() if result["success"] else None,
                error_message=result.get("error")
            )
            db.add(email)

            if result["success"]:
                sent_count += 1
                lead.status = "contacted"
            else:
                failed_count += 1

        campaign.status = CampaignStatus.ACTIVE
        campaign.emails_sent = sent_count
        await db.commit()

        return {
            "sent": sent_count,
            "failed": failed_count,
            "total": len(leads)
        }

    async def send_follow_ups(
        self,
        db: AsyncSession,
        campaign_id: int,
        max_steps: int = 3
    ) -> Dict[str, Any]:
        """Send follow-up emails based on sequence."""
        campaign = await db.get(Campaign, campaign_id)
        follow_up_days = [1, 3, 7]  # Days between follow-ups

        sent_count = 0
        failed_count = 0

        for step in range(2, max_steps + 1):
            days_to_wait = follow_up_days[step - 2]

            # Get leads that need follow-up
            stmt = select(Lead).join(Email).where(
                Email.campaign_id == campaign_id,
                Email.sequence_step == step - 1,
                Email.status == EmailStatus.SENT,
                Email.sent_at <= datetime.utcnow() - timedelta(days=days_to_wait)
            ).distinct()

            result = await db.execute(stmt)
            leads_needing_followup = result.scalars().all()

            for lead in leads_needing_followup:
                # Get previous emails for this lead in this campaign
                prev_stmt = select(Email).where(
                    Email.lead_id == lead.id,
                    Email.campaign_id == campaign_id
                ).order_by(Email.sequence_step)
                prev_result = await db.execute(prev_stmt)
                previous_emails = prev_result.scalars().all()

                # Generate follow-up
                email_content = await self.personalizer.generate_follow_up(
                    lead={
                        "first_name": lead.first_name,
                        "last_name": lead.last_name,
                        "company": lead.company,
                        "title": lead.title
                    },
                    previous_emails=[{"subject": e.subject, "body": e.body} for e in previous_emails],
                    step=step
                )

                # Send
                result = await self.sender.send_email(
                    to_email=lead.email,
                    subject=email_content["subject"],
                    html_content=email_content["body"]
                )

                # Record
                email = Email(
                    lead_id=lead.id,
                    campaign_id=campaign_id,
                    subject=email_content["subject"],
                    body=email_content["body"],
                    status=EmailStatus.SENT if result["success"] else EmailStatus.FAILED,
                    sent_at=datetime.utcnow() if result["success"] else None,
                    sequence_step=step,
                    error_message=result.get("error")
                )
                db.add(email)

                if result["success"]:
                    sent_count += 1
                else:
                    failed_count += 1

        await db.commit()

        return {
            "sent": sent_count,
            "failed": failed_count
        }