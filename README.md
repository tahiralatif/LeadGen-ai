# LeadGen Agent

AI-powered lead generation and outreach automation for real estate agents.

## Features

- Automated lead discovery from multiple sources
- AI-powered personalization using mimo-v2.5
- Email outreach with follow-up sequences
- Response handling and meeting booking
- OpenClaw integration for natural language commands

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Configure API keys in `config/settings.py`
3. Set up PostgreSQL database
4. Run migrations: `python -m src.db.migrate`
5. Start the agent: `python -m src.main`

## Usage

```bash
# Find leads
python -m src.main find-leads --location "Austin, TX" --count 50

# Send campaign
python -m src.main send-campaign --leads-file leads.csv

# Check responses
python -m src.main check-responses
```

## Environment Variables

- `APOLLO_API_KEY` - Apollo.io API key
- `HUNTER_API_KEY` - Hunter.io API key
- `SENDGRID_API_KEY` - SendGrid API key
- `NEVERBOUNCE_API_KEY` - NeverBounce API key
- `DATABASE_URL` - PostgreSQL connection string
- `OPENAI_API_KEY` - OpenAI API key (for mimo-v2.5)