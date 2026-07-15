"""Configuration settings for LeadGen Agent."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# API Keys
APOLLO_API_KEY = os.getenv("APOLLO_API_KEY", "")
HUNTER_API_KEY = os.getenv("HUNTER_API_KEY", "")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
NEVERBOUNCE_API_KEY = os.getenv("NEVERBOUNCE_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://llm2.jugaar.ai/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "xiaomimimo/mimo-v2.5")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://leadgen:leadgen123@localhost:5432/leadgen")

# Email Settings
EMAIL_FROM = os.getenv("EMAIL_FROM", "your-name@yourdomain.com")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "Your Name")
EMAIL_REPLY_TO = os.getenv("EMAIL_REPLY_TO", "your-reply@yourdomain.com")

# Domain Settings
DOMAIN = os.getenv("DOMAIN", "yourdomain.com")

# Campaign Settings
MAX_EMAILS_PER_DAY = int(os.getenv("MAX_EMAILS_PER_DAY", "50"))
FOLLOW_UP_DAYS = [1, 3, 7]  # Days between follow-ups

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = BASE_DIR / "logs" / "leadgen.log"

# API Endpoints
APOLLO_BASE_URL = "https://api.apollo.io/v1"
HUNTER_BASE_URL = "https://api.hunter.io/v2"
NEVERBOUNCE_BASE_URL = "https://api.neverbounce.com/v4"