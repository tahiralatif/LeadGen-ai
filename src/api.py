"""FastAPI server for LeadGen Agent."""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from .openclaw.agent import LeadGenAgent
from .discovery.manager import DiscoveryManager
from .enrichment.verifier import EmailVerifier
from .outreach.campaign import CampaignManager
from .response.handler import ResponseHandler
from .db.connection import async_session
from .utils.analytics import Analytics

app = FastAPI(
    title="LeadGen Agent",
    description="AI-powered lead generation and outreach",
    version="1.0.0"
)

agent = LeadGenAgent()
discovery = DiscoveryManager()
verifier = EmailVerifier()


class FindLeadsRequest(BaseModel):
    location: str
    title: Optional[str] = "Real Estate Agent"
    count: Optional[int] = 50
    skip_verify: Optional[bool] = False


class CampaignRequest(BaseModel):
    name: str
    subject: str
    template: Optional[str] = None
    lead_emails: Optional[List[str]] = None


class CommandRequest(BaseModel):
    command: str


@app.get("/")
async def root():
    return {
        "name": "LeadGen Agent",
        "version": "1.0.0",
        "status": "running"
    }


@app.post("/leads/find")
async def find_leads(request: FindLeadsRequest):
    """Find and verify leads."""
    try:
        leads = await discovery.discover_leads(
            location=request.location,
            title=request.title,
            limit=request.count
        )

        if not request.skip_verify:
            for lead in leads:
                verification = await verifier.verify_email(lead["email"])
                lead["verified"] = verification["verified"]
                lead["verification_score"] = verification["score"]

        return {
            "success": True,
            "leads": leads,
            "total": len(leads)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/leads/verify")
async def verify_lead(email: str):
    """Verify a single email address."""
    try:
        result = await verifier.verify_email(email)
        return {
            "success": True,
            "verification": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/campaigns/send")
async def send_campaign(request: CampaignRequest):
    """Send an email campaign."""
    try:
        manager = CampaignManager()

        async with async_session() as db:
            campaign = await manager.create_campaign(
                db=db,
                name=request.name,
                subject_line=request.subject,
                message_template=request.template or "Hi {first_name}, I noticed you're a real estate agent in {location}. We help agents like you find more clients using AI. Would you like to learn more?"
            )

            return {
                "success": True,
                "campaign_id": campaign.id,
                "message": "Campaign created. Use /campaigns/{id}/send to send emails."
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/command")
async def process_command(request: CommandRequest):
    """Process a natural language command."""
    try:
        result = await agent.process_command(request.command)
        return {
            "success": True,
            "response": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    """Get overall statistics."""
    try:
        async with async_session() as db:
            analytics = Analytics(db)
            stats = await analytics.get_summary()
            return {
                "success": True,
                "stats": stats
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0"
    }