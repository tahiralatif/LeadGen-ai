# LeadGen AI

AI-powered lead generation and outreach automation for real estate agents.

## 🚀 Deployed URL

**http://69.12.84.135:8000**

- Landing Page: http://69.12.84.135:8000/landing
- Dashboard: http://69.12.84.135:8000/dashboard
- API Docs: http://69.12.84.135:8000/api/docs

## ✨ Features

### Lead Generation
- 🔍 Google Maps scraping with Camoufox browser
- 📧 Real email finder (website scraping + pattern guessing)
- 🎯 Multi-source lead discovery

### Email Intelligence
- 📬 Email open tracking (1x1 pixel)
- 🖱️ Click tracking for links
- 🔄 3-step follow-up sequences
- 📊 Campaign analytics

### User System
- 👤 Multi-user support
- 🔐 JWT authentication
- ⚙️ Per-user settings (Brevo API key)

### Professional UI
- 🏠 Landing page for non-logged users
- 📝 Email template editor
- 📈 Dashboard with stats

### Production Quality
- 🧪 24 unit tests
- ⚡ Rate limiting (100 req/min)
- 🛡️ Error handling middleware
- 📋 Request logging

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI + Python 3.12 |
| Database | PostgreSQL (asyncpg) |
| Browser | Camoufox |
| Email | Brevo API (free) |
| LLM | mimo-v2.5 |
| Auth | JWT + bcrypt |

## 📦 Setup

### Prerequisites
- Python 3.12+
- PostgreSQL
- Node.js (for browser binaries)

### Installation

```bash
# Clone repository
git clone https://github.com/tahiralatif/LeadGen-ai.git
cd LeadGen-ai

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup database
python -c "import asyncio; from src.db.connection import init_db; asyncio.run(init_db())"

# Start API server
uvicorn src.api:app --host 0.0.0.0 --port 8000
```

### Environment Variables

Create `.env` file:

```env
# LLM Configuration
LLM_API_URL=https://llm2.jugaar.ai/v1
LLM_MODEL=xiaomimimo/mimo-v2.5
LLM_API_KEY=your-api-key

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/leadgen

# JWT
JWT_SECRET_KEY=your-secret-key

# Email (User provides their own Brevo key in Settings)
```

## 📚 API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login |
| GET | `/api/auth/me` | Get current user |

### Leads
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/leads/find` | Find new leads |
| GET | `/api/leads` | Get all leads |
| DELETE | `/api/leads/{id}` | Delete lead |

### Campaigns
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/campaigns/send` | Create campaign |
| POST | `/api/campaigns/send-email` | Send single email |
| GET | `/api/campaigns/{id}/stats` | Get campaign stats |

### Follow-ups
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/followup/create` | Create follow-up sequence |
| GET | `/api/followup/{lead_id}/pending` | Get pending follow-ups |
| POST | `/api/followup/send-next` | Send next follow-up |

### Tracking
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/track/open/{email_id}` | Track email open |
| GET | `/api/track/click/{email_id}` | Track link click |

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_auth.py -v
```

## 📁 Project Structure

```
leadgen-agent/
├── src/
│   ├── api.py              # FastAPI server
│   ├── auth/               # Authentication
│   │   └── jwt.py          # JWT utilities
│   ├── db/                 # Database
│   │   ├── connection.py   # Async PostgreSQL
│   │   └── models.py       # SQLAlchemy models
│   ├── discovery/          # Lead discovery
│   │   ├── scraper.py      # Google Maps scraper
│   │   ├── email_finder.py # Email finder
│   │   └── manager.py      # Discovery coordinator
│   ├── middleware/          # Middleware
│   │   ├── rate_limiter.py # Rate limiting
│   │   └── error_handler.py # Error handling
│   ├── outreach/           # Email outreach
│   │   ├── sender.py       # Email sender
│   │   ├── tracker.py      # Open/click tracking
│   │   └── followup.py     # Follow-up sequences
│   └── personalization/    # AI personalization
│       └── engine.py       # mimo-v2.5 integration
├── static/                 # Frontend
│   ├── index.html          # Dashboard
│   ├── landing.html        # Landing page
│   └── templates.html      # Email templates
├── tests/                  # Unit tests
├── config/                 # Configuration
├── requirements.txt        # Python dependencies
└── .env                    # Environment variables
```

## 🎯 Usage

### Web Interface

1. Visit http://69.12.84.135:8000/landing
2. Click "Get Started" to register or login
3. **Pre-configured account:**
   - Email: `tara378581@gmail.com`
   - Password: `leadgen123`
4. Find leads and send campaigns

### Default Account

A pre-configured account is available with Brevo API key already set up:

| Field | Value |
|-------|-------|
| Email | tara378581@gmail.com |
| Password | leadgen123 |
| Brevo API | Configured ✓ |

### API Usage

```python
import requests

# Register
requests.post("http://69.12.84.135:8000/api/auth/register", json={
    "email": "you@example.com",
    "name": "Your Name",
    "password": "securepassword"
})

# Login
response = requests.post("http://69.12.84.135:8000/api/auth/login", json={
    "email": "you@example.com",
    "password": "securepassword"
})
token = response.json()["token"]

# Find leads
requests.post("http://69.12.84.135:8000/api/leads/find", 
    headers={"Authorization": f"Bearer {token}"},
    json={"location": "Austin, TX", "count": 10}
)
```

## 👥 Author

**Tahira Latif**
- GitHub: [@tahiralatif](https://github.com/tahiralatif)
- Email: tahira@jugaar.ai

## 📄 License

MIT License

## 🙏 Acknowledgments

- Built with ❤️ for real estate professionals
- Powered by AI (mimo-v2.5)
- Free tools: Brevo, Google Maps scraping