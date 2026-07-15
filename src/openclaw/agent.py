"""OpenClaw agent for natural language lead generation."""
import json
from typing import Dict, Any
from ..discovery.manager import DiscoveryManager
from ..enrichment.verifier import EmailVerifier
from ..outreach.campaign import CampaignManager
from ..response.handler import ResponseHandler
from ..db.connection import async_session
from ..db.models import Lead, Campaign


class LeadGenAgent:
    """Agent for OpenClaw integration."""

    def __init__(self):
        self.discovery = DiscoveryManager()
        self.verifier = EmailVerifier()
        self.campaign_manager = CampaignManager()
        self.response_handler = ResponseHandler()

    async def process_command(self, command: str) -> str:
        """Process a natural language command."""
        command = command.lower().strip()

        # Find leads
        if "find" in command and "lead" in command:
            return await self._handle_find_leads(command)

        # Send campaign
        elif "send" in command and "campaign" in command:
            return await self._handle_send_campaign(command)

        # Check responses
        elif "check" in command and "response" in command:
            return await self._handle_check_responses(command)

        # Show stats
        elif "stat" in command or "show" in command:
            return await self._handle_show_stats(command)

        else:
            return self._get_help_text()

    async def _handle_find_leads(self, command: str) -> str:
        """Handle find leads command."""
        # Extract location from command
        location = None
        if "in" in command:
            parts = command.split("in")
            if len(parts) > 1:
                location = parts[1].strip().split()[0:2]
                location = " ".join(location)

        if not location:
            return "Please specify a location. Example: 'Find leads in Austin, TX'"

        count = 10
        if any(char.isdigit() for char in command):
            for word in command.split():
                if word.isdigit():
                    count = int(word)
                    break

        try:
            leads = await self.discovery.discover_leads(
                location=location,
                limit=count
            )

            # Verify emails
            verified_count = 0
            for lead in leads:
                verification = await self.verifier.verify_email(lead["email"])
                if verification["verified"]:
                    verified_count += 1

            return f"Found {len(leads)} leads in {location}. {verified_count} verified."

        except Exception as e:
            return f"Error finding leads: {str(e)}"

    async def _handle_send_campaign(self, command: str) -> str:
        """Handle send campaign command."""
        return "Campaign sending requires configuration. Please set up your email templates and run: python -m src.main send-campaign --name 'My Campaign' --subject 'Subject Line'"

    async def _handle_check_responses(self, command: str) -> str:
        """Handle check responses command."""
        return "Response checking requires IMAP configuration. Please set up your email credentials and run: python -m src.main check-responses --imap-host imap.gmail.com --imap-user your@email.com --imap-password your-password"

    async def _handle_show_stats(self, command: str) -> str:
        """Handle show stats command."""
        try:
            async with async_session() as db:
                from sqlalchemy import func

                # Count leads
                lead_count = await db.scalar(func.count(Lead.id))

                # Count campaigns
                campaign_count = await db.scalar(func.count(Campaign.id))

                # Count emails sent
                from ..db.models import Email
                email_count = await db.scalar(func.count(Email.id))

                return f"""Current Statistics:
- Total Leads: {lead_count}
- Total Campaigns: {campaign_count}
- Total Emails Sent: {email_count}"""

        except Exception as e:
            return f"Error getting stats: {str(e)}"

    def _get_help_text(self) -> str:
        """Get help text."""
        return """Available commands:

1. Find leads: "Find 50 leads in Austin, TX"
2. Send campaign: "Send campaign to all leads"
3. Check responses: "Check for new responses"
4. Show stats: "Show me the statistics"

Examples:
- "Find 20 real estate agents in New York"
- "Send my first campaign"
- "Check for new responses"
- "Show me the statistics"
"""