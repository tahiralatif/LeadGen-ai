"""Database models and connection."""
from .models import Base, Lead, Campaign, Email, Response
from .connection import get_db, init_db