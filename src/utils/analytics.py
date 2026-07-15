"""Analytics and reporting."""
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from ..db.models import Lead, Campaign, Email, Response, LeadStatus, EmailStatus


class Analytics:
    """Track and report analytics."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_lead_stats(self) -> Dict[str, Any]:
        """Get lead statistics."""
        total = await self.db.scalar(select(func.count(Lead.id)))
        
        verified_result = await self.db.execute(
            select(func.count(Lead.id)).where(Lead.verified == True)
        )
        verified = verified_result.scalar()

        status_counts = {}
        for status in LeadStatus:
            result = await self.db.execute(
                select(func.count(Lead.id)).where(Lead.status == status)
            )
            status_counts[status.value] = result.scalar()

        return {
            "total_leads": total,
            "verified_leads": verified,
            "by_status": status_counts
        }

    async def get_campaign_stats(self, campaign_id: int = None) -> Dict[str, Any]:
        """Get campaign statistics."""
        if campaign_id:
            campaigns = [await self.db.get(Campaign, campaign_id)]
        else:
            result = await self.db.execute(select(Campaign))
            campaigns = result.scalars().all()

        stats = []
        for campaign in campaigns:
            # Get email stats
            sent_result = await self.db.execute(
                select(func.count(Email.id)).where(
                    Email.campaign_id == campaign.id,
                    Email.status == EmailStatus.SENT
                )
            )
            sent = sent_result.scalar()
            
            opened_result = await self.db.execute(
                select(func.count(Email.id)).where(
                    Email.campaign_id == campaign.id,
                    Email.status == EmailStatus.OPENED
                )
            )
            opened = opened_result.scalar()
            
            clicked_result = await self.db.execute(
                select(func.count(Email.id)).where(
                    Email.campaign_id == campaign.id,
                    Email.status == EmailStatus.CLICKED
                )
            )
            clicked = clicked_result.scalar()
            
            bounced_result = await self.db.execute(
                select(func.count(Email.id)).where(
                    Email.campaign_id == campaign.id,
                    Email.status == EmailStatus.BOUNCED
                )
            )
            bounced = bounced_result.scalar()

            stats.append({
                "campaign_id": campaign.id,
                "name": campaign.name,
                "status": campaign.status.value,
                "total_leads": campaign.total_leads,
                "emails_sent": sent,
                "opened": opened,
                "clicked": clicked,
                "bounced": bounced,
                "open_rate": (opened / sent * 100) if sent > 0 else 0,
                "click_rate": (clicked / sent * 100) if sent > 0 else 0,
                "bounce_rate": (bounced / sent * 100) if sent > 0 else 0
            })

        return {
            "campaigns": stats,
            "total_campaigns": len(campaigns)
        }

    async def get_response_stats(self) -> Dict[str, Any]:
        """Get response statistics."""
        total = await self.db.scalar(select(func.count(Response.id)))

        intent_counts = {}
        for intent in ["interested", "not_interested", "schedule", "question", "unsubscribe"]:
            result = await self.db.execute(
                select(func.count(Response.id)).where(Response.intent == intent)
            )
            intent_counts[intent] = result.scalar()

        email_count_result = await self.db.execute(select(func.count(Email.id)))
        email_count = email_count_result.scalar()

        return {
            "total_responses": total,
            "by_intent": intent_counts,
            "response_rate": (total / email_count * 100) if email_count > 0 else 0
        }

    async def get_daily_stats(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get daily statistics for the last N days."""
        stats = []
        for i in range(days):
            date = datetime.utcnow().date() - timedelta(days=i)
            start = datetime.combine(date, datetime.min.time())
            end = datetime.combine(date, datetime.max.time())

            leads_result = await self.db.execute(
                select(func.count(Lead.id)).where(
                    Lead.created_at.between(start, end)
                )
            )
            leads = leads_result.scalar()
            
            emails_result = await self.db.execute(
                select(func.count(Email.id)).where(
                    Email.sent_at.between(start, end)
                )
            )
            emails = emails_result.scalar()
            
            responses_result = await self.db.execute(
                select(func.count(Response.id)).where(
                    Response.created_at.between(start, end)
                )
            )
            responses = responses_result.scalar()

            stats.append({
                "date": date.isoformat(),
                "leads_found": leads,
                "emails_sent": emails,
                "responses_received": responses
            })

        return stats

    async def get_summary(self) -> Dict[str, Any]:
        """Get overall summary."""
        lead_stats = await self.get_lead_stats()
        campaign_stats = await self.get_campaign_stats()
        response_stats = await self.get_response_stats()

        return {
            "leads": lead_stats,
            "campaigns": campaign_stats,
            "responses": response_stats,
            "generated_at": datetime.utcnow().isoformat()
        }