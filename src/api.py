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
from .outreach.tracker import EmailTracker, ReplyDetector
from .outreach.followup import FollowUpSequence
from .response.handler import ResponseHandler
from .db.connection import async_session
from .db.models import User, Lead, Campaign, Email, EmailStatus, Response
from .utils.analytics import Analytics
from .auth.jwt import (
    hash_password, verify_password, create_access_token,
    get_current_user, decode_token
)
from .middleware import RateLimitMiddleware, ErrorHandlerMiddleware, RequestLoggingMiddleware
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

app = FastAPI(
    title="LeadGen Agent",
    description="AI-powered lead generation and outreach",
    version="3.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Add middleware (order matters - last added = first executed)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)

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
    title: Optional[str] = None
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
    industry: Optional[str] = "real_estate"
    custom_industry: Optional[str] = None
    service_description: Optional[str] = None


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
            "industry": user.industry,
            "custom_industry": user.custom_industry,
            "service_description": user.service_description,
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
        db_user = await db.merge(user)
        if request.name:
            db_user.name = request.name
        if request.brevo_api_key is not None:
            db_user.brevo_api_key = request.brevo_api_key
        if request.industry:
            db_user.industry = request.industry
        if request.custom_industry is not None:
            db_user.custom_industry = request.custom_industry
        if request.service_description is not None:
            db_user.service_description = request.service_description

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


@app.get("/landing")
async def landing():
    """Serve the landing page."""
    return FileResponse(str(static_dir / "landing.html"))


@app.get("/templates")
async def templates():
    """Serve the email templates page."""
    return FileResponse(str(static_dir / "templates.html"))


@app.get("/analytics")
async def analytics():
    """Serve the email analytics page."""
    return FileResponse(str(static_dir / "analytics.html"))


@app.get("/api/leads/{lead_id}/emails")
async def get_lead_emails(
    lead_id: int,
    user: User = Depends(get_current_user)
):
    """Get all emails for a specific lead."""
    async with async_session() as db:
        result = await db.execute(
            select(Email)
            .where(Email.lead_id == lead_id)
            .order_by(Email.created_at.desc())
        )
        emails = result.scalars().all()
        
        return {
            "success": True,
            "emails": [
                {
                    "id": email.id,
                    "lead_id": email.lead_id,
                    "subject": email.subject,
                    "body": email.body,
                    "status": email.status.value if hasattr(email.status, 'value') else email.status,
                    "sequence_step": email.sequence_step,
                    "sent_at": email.sent_at.isoformat() if email.sent_at else None,
                    "opened_at": email.opened_at.isoformat() if email.opened_at else None,
                    "clicked_at": email.clicked_at.isoformat() if email.clicked_at else None,
                    "bounced_at": email.bounced_at.isoformat() if email.bounced_at else None,
                    "error_message": email.error_message,
                    "created_at": email.created_at.isoformat() if email.created_at else None
                }
                for email in emails
            ]
        }


@app.get("/api/emails/all")
async def get_all_emails(
    user: User = Depends(get_current_user)
):
    """Get ALL emails sent by this user."""
    async with async_session() as db:
        result = await db.execute(
            select(Email)
            .order_by(Email.created_at.desc())
        )
        emails = result.scalars().all()
        
        # Also get lead info for each email
        emails_with_lead = []
        for email in emails:
            lead_info = None
            if email.lead_id:
                lead_result = await db.execute(
                    select(Lead).where(Lead.id == email.lead_id)
                )
                lead = lead_result.scalar_one_or_none()
                if lead:
                    lead_info = {
                        "id": lead.id,
                        "email": lead.email,
                        "company": lead.company,
                        "phone": lead.phone,
                        "source": lead.source
                    }
            
            emails_with_lead.append({
                "id": email.id,
                "lead_id": email.lead_id,
                "recipient_email": email.recipient_email,
                "subject": email.subject,
                "body": email.body,
                "status": email.status.value if hasattr(email.status, 'value') else email.status,
                "sequence_step": email.sequence_step,
                "sent_at": email.sent_at.isoformat() if email.sent_at else None,
                "opened_at": email.opened_at.isoformat() if email.opened_at else None,
                "clicked_at": email.clicked_at.isoformat() if email.clicked_at else None,
                "bounced_at": email.bounced_at.isoformat() if email.bounced_at else None,
                "error_message": email.error_message,
                "created_at": email.created_at.isoformat() if email.created_at else None,
                "lead": lead_info
            })
        
        return {
            "success": True,
            "emails": emails_with_lead
        }


# ===== Lead Endpoints =====

@app.post("/api/leads/find")
async def find_leads(
    request: FindLeadsRequest,
    user: User = Depends(get_current_user)
):
    """Find and verify leads."""
    try:
        # Auto-generate search query based on user's industry if no title provided
        search_query = request.title
        if not search_query and user.industry:
            industry_queries = {
                "real_estate": "real estate agency",
                "ai_engineer": "software company",
                "web_developer": "digital marketing agency",
                "freelancer": "startup",
                "marketing": "ecommerce store",
                "consultant": "accounting firm",
                "saas": "saas startup",
                "ecommerce": "online store",
                "healthcare": "medical clinic",
                "education": "training center",
                "other": "business"
            }
            search_query = industry_queries.get(user.industry, "business")
        if not search_query:
            search_query = "software company"
        
        print(f"DEBUG: search_query={search_query}, industry={user.industry}")
        leads = await discovery.discover_leads(
            location=request.location,
            title=search_query,
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
    """Send a single email using user's own API key with tracking."""
    try:
        if not user.brevo_api_key:
            return {"success": False, "error": "Please configure your Brevo API key in Settings"}

        tracker = EmailTracker()

        # Save email record first to get ID
        async with async_session() as db:
            email_record = Email(
                lead_id=None,
                recipient_email=request.to_email,
                subject=request.subject,
                body=request.body,
                status=EmailStatus.PENDING
            )
            db.add(email_record)
            await db.commit()
            await db.refresh(email_record)
            email_id = email_record.id

        # Add tracking pixel for open tracking
        tracking_pixel = tracker.generate_tracking_pixel(email_id)

        # Convert plain text to HTML with tracking
        body_html = request.body.replace("\n", "<br>")
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            {body_html}
            {tracking_pixel}
        </body>
        </html>
        """

        # Send using user's Brevo API key
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.brevo.com/v3/smtp/email",
                json={
                    "sender": {
                        "name": user.name or "LeadGen AI",
                        "email": "tara378581@gmail.com"
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

                # Update email record with sent status
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

                return {
                    "success": True,
                    "message_id": data.get("messageId"),
                    "email_id": email_id
                }
            else:
                # Update email record with failed status
                async with async_session() as db:
                    await db.execute(
                        update(Email)
                        .where(Email.id == email_id)
                        .values(
                            status=EmailStatus.FAILED,
                            error_message=f"API error: {response.status_code}"
                        )
                    )
                    await db.commit()

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
                .outerjoin(Lead, Email.lead_id == Lead.id)
                .where((Lead.user_id == user.id) | (Email.lead_id.is_(None)))
            )
            total_emails = email_result.scalar() or 0

            # Count opened emails
            opened_result = await db.execute(
                select(func.count(Email.id))
                .outerjoin(Lead, Email.lead_id == Lead.id)
                .where(((Lead.user_id == user.id) | (Email.lead_id.is_(None))) & Email.opened_at.isnot(None))
            )
            total_opened = opened_result.scalar() or 0

            # Count clicked emails
            clicked_result = await db.execute(
                select(func.count(Email.id))
                .outerjoin(Lead, Email.lead_id == Lead.id)
                .where(((Lead.user_id == user.id) | (Email.lead_id.is_(None))) & Email.clicked_at.isnot(None))
            )
            total_clicked = clicked_result.scalar() or 0

            return {
                "success": True,
                "stats": {
                    "total_leads": total_leads,
                    "total_campaigns": total_campaigns,
                    "total_emails": total_emails,
                    "total_opened": total_opened,
                    "total_clicked": total_clicked
                }
            }
    except Exception as e:
        return {"success": True, "stats": {"total_leads": 0, "total_campaigns": 0, "total_emails": 0, "total_opened": 0, "total_clicked": 0}}


# ===== Tracking Endpoints =====

@app.get("/api/track/open/{email_id}")
async def track_open(email_id: int):
    """Track email open - returns 1x1 tracking pixel."""
    tracker = EmailTracker()
    pixel = await tracker.track_open(email_id)
    from fastapi.responses import Response
    return Response(content=pixel, media_type="image/gif")


@app.get("/api/track/click/{email_id}")
async def track_click(email_id: int, url: str):
    """Track link click - redirects to original URL."""
    tracker = EmailTracker()
    redirect_url = await tracker.track_click(email_id, url)
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=redirect_url)


@app.get("/api/campaigns/{campaign_id}/stats")
async def get_campaign_stats(
    campaign_id: int,
    user: User = Depends(get_current_user)
):
    """Get campaign tracking statistics."""
    tracker = EmailTracker()
    stats = await tracker.get_campaign_stats(campaign_id)
    return {"success": True, "stats": stats}


# ===== Follow-up Endpoints =====

@app.post("/api/followup/create")
async def create_followup(
    lead_id: int,
    campaign_id: int,
    subject: str,
    message: str,
    user: User = Depends(get_current_user)
):
    """Create follow-up sequence for a lead."""
    followup = FollowUpSequence()
    email_ids = await followup.create_sequence(
        lead_id=lead_id,
        campaign_id=campaign_id,
        subject=subject,
        message=message
    )
    return {"success": True, "email_ids": email_ids, "total_steps": len(email_ids)}


@app.get("/api/followup/{lead_id}/pending")
async def get_pending_followups(
    lead_id: int,
    user: User = Depends(get_current_user)
):
    """Get pending follow-ups for a lead."""
    followup = FollowUpSequence()
    pending = await followup.get_pending_follow_ups(lead_id)
    return {"success": True, "pending": pending}


@app.post("/api/followup/send-next")
async def send_next_followup(
    lead_id: int,
    user: User = Depends(get_current_user)
):
    """Send next follow-up email."""
    followup = FollowUpSequence()

    if not user.brevo_api_key:
        return {"success": False, "error": "Please configure your Brevo API key"}

    result = await followup.send_next_follow_up(
        lead_id=lead_id,
        api_key=user.brevo_api_key,
        sender_email=user.email,
        sender_name=user.name
    )

    if result:
        return {"success": True, "result": result}
    else:
        return {"success": False, "error": "No pending follow-ups"}


@app.delete("/api/followup/{lead_id}/{campaign_id}")
async def cancel_followup(
    lead_id: int,
    campaign_id: int,
    user: User = Depends(get_current_user)
):
    """Cancel follow-up sequence."""
    followup = FollowUpSequence()
    await followup.cancel_sequence(lead_id, campaign_id)
    return {"success": True, "message": "Follow-up sequence cancelled"}


# ===== Health Check =====

@app.get("/health")
async def health():
    """Health check endpoint with system status."""
    from datetime import datetime
    import os

    # Check database connectivity
    db_status = "healthy"
    try:
        from sqlalchemy import text
        async with async_session() as db:
            await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy",
        "version": "3.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": db_status,
            "api": "healthy"
        },
        "system": {
            "pid": os.getpid(),
            "uptime": datetime.utcnow().isoformat()
        }
    }