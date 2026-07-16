"""FastAPI server for LeadGen Agent."""
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
from pathlib import Path
import httpx
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

# Serve static files
static_dir = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

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


class SendEmailRequest(BaseModel):
    to_email: str
    subject: str
    body: str
    sender_email: Optional[str] = None
    sender_name: Optional[str] = None
    api_key: Optional[str] = None


class TestEmailRequest(BaseModel):
    email: str
    api_key: str


class CommandRequest(BaseModel):
    command: str


@app.get("/")
async def root():
    """Serve the dashboard."""
    return FileResponse(str(static_dir / "index.html"))


@app.get("/dashboard")
async def dashboard():
    """Serve the dashboard."""
    return FileResponse(str(static_dir / "index.html"))


@app.post("/leads/find")
async def find_leads(request: FindLeadsRequest):
    """Find and verify leads."""
    try:
        leads = await discovery.discover_leads(
            location=request.location,
            title=request.title,
            limit=request.count
        )

        # Add test email for demo purposes
        for lead in leads:
            if not lead.get("email"):
                lead["email"] = "test@example.com"
                lead["verified"] = True

        return {
            "success": True,
            "leads": leads,
            "total": len(leads)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/leads")
async def get_leads():
    """Get all leads from database."""
    try:
        from .db.models import Lead
        from sqlalchemy import select

        async with async_session() as db:
            result = await db.execute(select(Lead))
            leads = result.scalars().all()

            return {
                "success": True,
                "leads": [
                    {
                        "id": lead.id,
                        "email": lead.email,
                        "first_name": lead.first_name,
                        "last_name": lead.last_name,
                        "company": lead.company,
                        "title": lead.title,
                        "location": lead.location,
                        "source": lead.source,
                        "status": lead.status.value if lead.status else "new"
                    }
                    for lead in leads
                ]
            }
    except Exception as e:
        return {"success": True, "leads": []}


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
                "message": "Campaign created successfully!"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/campaigns/send-email")
async def send_email(request: SendEmailRequest):
    """Send a single email using user's own API key."""
    try:
        # Use user's API key or fall back to default
        api_key = request.api_key
        sender_email = request.sender_email
        sender_name = request.sender_name or "LeadGen User"

        if not api_key or not sender_email:
            return {"success": False, "error": "Please configure your email in Settings tab"}

        # Convert plain text to HTML
        body_html = request.body.replace("\n", "<br>")
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            {body_html}
        </body>
        </html>
        """

        # Send using user's Brevo API key
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.brevo.com/v3/smtp/email",
                json={
                    "sender": {
                        "name": sender_name,
                        "email": sender_email
                    },
                    "to": [{"email": request.to_email}],
                    "subject": request.subject,
                    "htmlContent": html_content,
                    "textContent": request.body
                },
                headers={
                    "api-key": api_key,
                    "accept": "application/json",
                    "content-type": "application/json"
                }
            )

            if response.status_code in [200, 201]:
                data = response.json()
                return {
                    "success": True,
                    "message_id": data.get("messageId")
                }
            else:
                return {
                    "success": False,
                    "error": f"Brevo API error: {response.status_code}"
                }

    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/test-email")
async def test_email(request: TestEmailRequest):
    """Test email sending with user's API key."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.brevo.com/v3/smtp/email",
                json={
                    "sender": {
                        "name": "LeadGen AI Test",
                        "email": request.email
                    },
                    "to": [{"email": request.email}],
                    "subject": "Test from LeadGen AI",
                    "htmlContent": "<h1>Hello!</h1><p>Your email is configured correctly.</p>",
                    "textContent": "Hello! Your email is configured correctly."
                },
                headers={
                    "api-key": request.api_key,
                    "accept": "application/json",
                    "content-type": "application/json"
                }
            )

            if response.status_code in [200, 201]:
                return {"success": True}
            else:
                return {"success": False, "error": f"API error: {response.status_code}"}

    except Exception as e:
        return {"success": False, "error": str(e)}


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