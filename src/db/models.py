"""Database models."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship, DeclarativeBase
import enum


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    brevo_api_key = Column(String(500))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    leads = relationship("Lead", back_populates="user")
    campaigns = relationship("Campaign", back_populates="user")


class LeadStatus(enum.Enum):
    NEW = "new"
    CONTACTED = "contacted"
    REPLIED = "replied"
    INTERESTED = "interested"
    MEETING_BOOKED = "meeting_booked"
    CONVERTED = "converted"
    UNSUBSCRIBED = "unsubscribed"


class CampaignStatus(enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class EmailStatus(enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    FAILED = "failed"


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    email = Column(String(255), index=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    company = Column(String(255))
    title = Column(String(255))
    phone = Column(String(50))
    location = Column(String(255))
    source = Column(String(50))  # apollo, hunter, manual, google_maps
    status = Column(Enum(LeadStatus), default=LeadStatus.NEW)
    verified = Column(Boolean, default=False)
    verification_score = Column(Integer)  # 0-100
    email_source = Column(String(50))  # website, contact_page, guessed
    email_confidence = Column(Integer)  # 0-100
    unsubscribed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="leads")
    emails = relationship("Email", back_populates="lead")
    responses = relationship("Response", back_populates="lead")


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    status = Column(Enum(CampaignStatus), default=CampaignStatus.DRAFT)
    subject_line = Column(String(500))
    message_template = Column(Text)
    follow_up_template = Column(Text)
    total_leads = Column(Integer, default=0)
    emails_sent = Column(Integer, default=0)
    replies_received = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="campaigns")
    emails = relationship("Email", back_populates="campaign")


class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"))
    subject = Column(String(500))
    body = Column(Text)
    status = Column(Enum(EmailStatus), default=EmailStatus.PENDING)
    sequence_step = Column(Integer, default=1)  # 1, 2, 3 for follow-ups
    sent_at = Column(DateTime)
    opened_at = Column(DateTime)
    clicked_at = Column(DateTime)
    bounced_at = Column(DateTime)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    lead = relationship("Lead", back_populates="emails")
    campaign = relationship("Campaign", back_populates="emails")


class Response(Base):
    __tablename__ = "responses"

    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    email_id = Column(Integer, ForeignKey("emails.id"))
    content = Column(Text)
    intent = Column(String(50))  # interested, not_interested, schedule, question
    sentiment = Column(String(20))  # positive, neutral, negative
    auto_replied = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    lead = relationship("Lead", back_populates="responses")