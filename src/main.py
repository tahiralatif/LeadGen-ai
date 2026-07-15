"""Main entry point for LeadGen Agent."""
import asyncio
import argparse
import json
from datetime import datetime
from .db.connection import init_db, async_session
from .db.models import Lead, Campaign, LeadStatus
from .discovery.manager import DiscoveryManager
from .enrichment.verifier import EmailVerifier
from .outreach.campaign import CampaignManager
from .response.handler import ResponseHandler


async def find_leads(args):
    """Find and verify leads."""
    print(f"Finding {args.count} leads in {args.location}...")

    discovery = DiscoveryManager()
    verifier = EmailVerifier()

    # Discover leads
    leads = await discovery.discover_leads(
        location=args.location,
        title=args.title or "Real Estate Agent",
        limit=args.count
    )
    print(f"Found {len(leads)} raw leads")

    # Verify emails
    if not args.skip_verify:
        print("Verifying emails...")
        for lead in leads:
            verification = await verifier.verify_email(lead["email"])
            lead["verified"] = verification["verified"]
            lead["verification_score"] = verification["score"]

        # Filter verified leads
        leads = [l for l in leads if l.get("verified", False)]
        print(f"After verification: {len(leads)} leads")

    # Save to database
    async with async_session() as db:
        for lead_data in leads:
            lead = Lead(
                email=lead_data["email"],
                first_name=lead_data.get("first_name"),
                last_name=lead_data.get("last_name"),
                company=lead_data.get("company"),
                title=lead_data.get("title"),
                phone=lead_data.get("phone"),
                location=lead_data.get("location"),
                source=lead_data.get("source", "manual"),
                verified=lead_data.get("verified", False),
                verification_score=lead_data.get("verification_score")
            )
            db.add(lead)
        await db.commit()

    # Output results
    output_file = f"leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w") as f:
        json.dump(leads, f, indent=2)

    print(f"Saved {len(leads)} leads to {output_file}")
    return leads


async def send_campaign(args):
    """Send email campaign."""
    print(f"Sending campaign: {args.name}")

    manager = CampaignManager()

    async with async_session() as db:
        # Create campaign
        campaign = await manager.create_campaign(
            db=db,
            name=args.name,
            subject_line=args.subject,
            message_template=args.template or "Hi {first_name}, I noticed you're a real estate agent in {location}. We help agents like you find more clients using AI. Would you like to learn more?",
            follow_up_template=args.follow_up_template
        )

        # Get leads
        if args.leads_file:
            with open(args.leads_file) as f:
                lead_emails = json.load(f)
            # Filter to only existing leads
            from sqlalchemy import select
            stmt = select(Lead).where(Lead.email.in_([l["email"] for l in lead_emails]))
            result = await db.execute(stmt)
            leads = result.scalars().all()
        else:
            from sqlalchemy import select
            stmt = select(Lead).where(Lead.status == LeadStatus.NEW)
            result = await db.execute(stmt)
            leads = result.scalars().all()

        lead_ids = [l.id for l in leads]
        await manager.add_leads_to_campaign(db, campaign.id, lead_ids)

        # Send emails
        print(f"Sending to {len(leads)} leads...")
        results = await manager.send_initial_emails(db, campaign.id)

        print(f"Campaign sent: {results['sent']} successful, {results['failed']} failed")


async def check_responses(args):
    """Check for and handle responses."""
    print("Checking for new responses...")

    handler = ResponseHandler()

    # Check inbox
    responses = await handler.check_inbox(
        imap_host=args.imap_host,
        imap_port=int(args.imap_port),
        username=args.imap_user,
        password=args.imap_password
    )

    print(f"Found {len(responses)} new responses")

    # Classify and respond
    for resp in responses:
        intent = await handler.classify_intent(resp["body"])
        print(f"From: {resp['from']}")
        print(f"Intent: {intent['intent']}")
        print(f"Sentiment: {intent['sentiment']}")
        print("---")


def main():
    parser = argparse.ArgumentParser(description="LeadGen Agent")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Find leads command
    find_parser = subparsers.add_parser("find-leads", help="Find leads")
    find_parser.add_argument("--location", required=True, help="Location to search")
    find_parser.add_argument("--title", help="Job title to search")
    find_parser.add_argument("--count", type=int, default=50, help="Number of leads")
    find_parser.add_argument("--skip-verify", action="store_true", help="Skip email verification")

    # Send campaign command
    send_parser = subparsers.add_parser("send-campaign", help="Send campaign")
    send_parser.add_argument("--name", required=True, help="Campaign name")
    send_parser.add_argument("--subject", required=True, help="Email subject")
    send_parser.add_argument("--template", help="Email template")
    send_parser.add_argument("--follow-up-template", help="Follow-up template")
    send_parser.add_argument("--leads-file", help="JSON file with leads")

    # Check responses command
    check_parser = subparsers.add_parser("check-responses", help="Check responses")
    check_parser.add_argument("--imap-host", required=True, help="IMAP host")
    check_parser.add_argument("--imap-port", default="993", help="IMAP port")
    check_parser.add_argument("--imap-user", required=True, help="IMAP username")
    check_parser.add_argument("--imap-password", required=True, help="IMAP password")

    args = parser.parse_args()

    if args.command == "find-leads":
        asyncio.run(find_leads(args))
    elif args.command == "send-campaign":
        asyncio.run(send_campaign(args))
    elif args.command == "check-responses":
        asyncio.run(check_responses(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()