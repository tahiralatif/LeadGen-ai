"""FastAPI server for LeadGen Agent."""
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from pathlib import Path
from datetime import datetime
import httpx
from .openclaw.agent import LeadGenAgent
from .discovery.manager import DiscoveryManager
from .enrichment.verifier import EmailVerifier
from .outreach.campaign import CampaignManager
from .response.handler import ResponseHandler
from .db.connection import async_session
from .db.models import User, Lead, Campaign, Email, Response
from .utils.analytics import Analytics
from .auth.jwt import (
    hash_password, verify_password, create_access_token,
    get_current_user, decode_token
)
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

app = FastAPI(
    title="LeadGen Agent",
    description="AI-powered lead generation and outreach",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
static_dir = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

agent = LeadGenAgent()
discovery = DiscoveryManager()
verifier = EmailVerifier()


# ===== Request Models =====

class RegisterRequest(BaseModel):
    email: EmailStr
    name: str
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


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


class TestEmailRequest(BaseModel):
    email: str
    api_key: str


class CommandRequest(BaseModel):
    command: str


class SettingsRequest(BaseModel):
    name: Optional[str] = None
    brevo_api_key: Optional[str] = None


# ===== Auth Endpoints =====

@app.post("/api/auth/register")
async def register(request: RegisterRequest):
    """Register a new user."""
    async with async_session() as db:
        # Check if user exists
        result = await db.execute(select(User).where(User.email == request.email))
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        # Create user
        user = User(
            email=request.email,
            name=request.name,
            hashed_password=hash_password(request.password)
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        # Create token
        token = create_access_token(data={"sub": str(user.id)})

        return {
            "success": True,
            "token": token,
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name
            }
        }


@app.post("/api/auth/login")
async def login(request: LoginRequest):
    """Login with email and password."""
    async with async_session() as db:
        result = await db.execute(select(User).where(User.email == request.email))
        user = result.scalar_one_or_none()

        if not user or not verify_password(request.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        token = create_access_token(data={"sub": str(user.id)})

        return {
            "success": True,
            "token": token,
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "brevo_api_key": user.brevo_api_key
            }
        }


@app.get("/api/auth/me")
async def get_me(user: User = Depends(get_current_user)):
    """Get current user info."""
    return {
        "success": True,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "brevo_api_key": user.brevo_api_key,
            "created_at": user.created_at.isoformat()
        }
    }


# ===== Settings Endpoints =====

@app.put("/api/settings")
async def update_settings(
    request: SettingsRequest,
    user: User = Depends(get_current_user)
):
    """Update user settings."""
    async with async_session() as db:
        if request.name:
            user.name = request.name
        if request.brevo_api_key is not None:
            user.brevo_api_key = request.brevo_api_key

        await db.commit()
        return {"success": True, "message": "Settings updated"}


# ===== Dashboard Endpoints =====

@app.get("/")
async def root():
    """Serve the dashboard."""
    return FileResponse(str(static_dir / "index.html"))


@app.get("/dashboard")
async def dashboard():
    """Serve the dashboard."""
    return FileResponse(str(static_dir / "index.html"))


# ===== Lead Endpoints =====

@app.post("/api/leads/find")
async def find_leads(
    request: FindLeadsRequest,
    user: User = Depends(get_current_user)
):
    """Find and verify leads."""
    try:
        leads = await discovery.discover_leads(
            location=request.location,
            title=request.title,
            limit=request.count
        )

        # Save leads to database with user_id
        async with async_session() as db:
            saved_leads = []
            for lead_data in leads:
                lead = Lead(
                    user_id=user.id,
                    email=lead_data.get("email"),
                    first_name=lead_data.get("first_name"),
                    last_name=lead_data.get("last_name"),
                    company=lead_data.get("company"),
                    title=lead_data.get("title"),
                    phone=lead_data.get("phone"),
                    location=lead_data.get("location"),
                    source=lead_data.get("source", "google_maps"),
                    email_source=lead_data.get("email_source"),
                    email_confidence=lead_data.get("email_confidence")
                )
                db.add(lead)
                saved_leads.append(lead)

            await db.commit()

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
                        "phone": lead.phone,
                        "location": lead.location,
                        "source": lead.source,
                        "email_source": lead.email_source,
                        "email_confidence": lead.email_confidence
                    }
                    for lead in saved_leads
                ],
                "total": len(saved_leads)
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/leads")
async def get_leads(
    user: User = Depends(get_current_user)
):
    """Get all leads for current user."""
    try:
        async with async_session() as db:
            result = await db.execute(
                select(Lead).where(Lead.user_id == user.id).order_by(Lead.created_at.desc())
            )
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
                        "phone": lead.phone,
                        "location": lead.location,
                        "source": lead.source,
                        "status": lead.status.value if lead.status else "new",
                        "email_source": lead.email_source,
                        "email_confidence": lead.email_confidence,
                        "created_at": lead.created_at.isoformat()
                    }
                    for lead in leads
                ]
            }
    except Exception as e:
        return {"success": True, "leads": []}


@app.delete("/api/leads/{lead_id}")
async def delete_lead(
    lead_id: int,
    user: User = Depends(get_current_user)
):
    """Delete a lead."""
    async with async_session() as db:
        result = await db.execute(
            select(Lead).where(Lead.id == lead_id, Lead.user_id == user.id)
        )
        lead = result.scalar_one_or_none()

        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")

        await db.delete(lead)
        await db.commit()

        return {"success": True, "message": "Lead deleted"}


# ===== Campaign Endpoints =====

@app.post("/api/campaigns/send")
async def send_campaign(
    request: CampaignRequest,
    user: User = Depends(get_current_user)
):
    """Send an email campaign."""
    try:
        async with async_session() as db:
            campaign = Campaign(
                user_id=user.id,
                name=request.name,
                subject_line=request.subject,
                message_template=request.template or "Hi {first_name}, I noticed you're a real estate agent in {location}. We help agents like you find more clients using AI. Would you like to learn more?",
                status="draft"
            )
            db.add(campaign)
            await db.commit()
            await db.refresh(campaign)

            return {
                "success": True,
                "campaign_id": campaign.id,
                "message": "Campaign created successfully!"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/campaigns")
async def get_campaigns(
    user: User = Depends(get_current_user)
):
    """Get all campaigns for current user."""
    try:
        async with async_session() as db:
            result = await db.execute(
                select(Campaign).where(Campaign.user_id == user.id).order_by(Campaign.created_at.desc())
            )
            campaigns = result.scalars().all()

            return {
                "success": True,
                "campaigns": [
                    {
                        "id": campaign.id,
                        "name": campaign.name,
                        "status": campaign.status.value if hasattr(campaign.status, 'value') else campaign.status,
                        "subject_line": campaign.subject_line,
                        "total_leads": campaign.total_leads,
                        "emails_sent": campaign.emails_sent,
                        "replies_received": campaign.replies_received,
                        "created_at": campaign.created_at.isoformat()
                    }
                    for campaign in campaigns
                ]
            }
    except Exception as e:
        return {"success": True, "campaigns": []}


# ===== Email Endpoints =====

@app.post("/api/campaigns/send-email")
async def send_email(
    request: SendEmailRequest,
    user: User = Depends(get_current_user)
):
    """Send a single email using user's own API key."""
    try:
        if not user.brevo_api_key:
            return {"success": False, "error": "Please configure your Brevo API key in Settings"}

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
                        "name": user.name,
                        "email": user.email
                    },
                    "to": [{"email": request.to_email}],
                    "subject": request.subject,
                    "htmlContent": html_content,
                    "textContent": request.body
                },
                headers={
                    "api-key": user.brevo_api_key,
                    "accept": "application/json",
                    "content-type": "application/json"
                }
            )

            if response.status_code in [200, 201]:
                data = response.json()

                # Save email record
                async with async_session() as db:
                    email_record = Email(
                        lead_id=0,
                        subject=request.subject,
                        body=request.body,
                        status="sent",
                        sent_at=datetime.utcnow()
                    )
                    db.add(email_record)
                    await db.commit()

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


# ===== Command Endpoints =====

@app.post("/api/command")
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


# ===== Stats Endpoints =====

@app.get("/api/stats")
async def get_stats(
    user: User = Depends(get_current_user)
):
    """Get statistics for current user."""
    try:
        async with async_session() as db:
            # Count user's leads
            lead_result = await db.execute(
                select(func.count(Lead.id)).where(Lead.user_id == user.id)
            )
            total_leads = lead_result.scalar() or 0

            # Count user's campaigns
            campaign_result = await db.execute(
                select(func.count(Campaign.id)).where(Campaign.user_id == user.id)
            )
            total_campaigns = campaign_result.scalar() or 0

            # Count emails sent
            email_result = await db.execute(
                select(func.count(Email.id))
                .join(Lead)
                .where(Lead.user_id == user.id)
            )
            total_emails = email_result.scalar() or 0

            return {
                "success": True,
                "stats": {
                    "total_leads": total_leads,
                    "total_campaigns": total_campaigns,
                    "total_emails": total_emails
                }
            }
    except Exception as e:
        return {"success": True, "stats": {"total_leads": 0, "total_campaigns": 0, "total_emails": 0}}


# ===== Health Check =====

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "2.0.0"
    }