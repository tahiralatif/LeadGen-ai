#!/bin/bash

# LeadGen Agent Setup Script

echo "Setting up LeadGen Agent..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright browsers
echo "Installing Playwright browsers..."
playwright install chromium

# Create logs directory
mkdir -p logs

# Create .env file template
if [ ! -f .env ]; then
    cat > .env << EOF
# API Keys
APOLLO_API_KEY=your_apollo_api_key
HUNTER_API_KEY=your_hunter_api_key
SENDGRID_API_KEY=your_sendgrid_api_key
NEVERBOUNCE_API_KEY=your_neverbounce_api_key

# OpenAI/mimo-v2.5
OPENAI_API_KEY=sk-proxy-33c534e29bcfc474861feee8231b6abb8f79dd9ab33f7776
OPENAI_BASE_URL=https://llm2.jugaar.ai/v1
OPENAI_MODEL=xiaomimimo/mimo-v2.5

# Database
DATABASE_URL=postgresql://localhost:5432/leadgen

# Email Settings
EMAIL_FROM=your-email@yourdomain.com
EMAIL_FROM_NAME=Your Name
EMAIL_REPLY_TO=your-reply@yourdomain.com

# Domain
DOMAIN=yourdomain.com

# Limits
MAX_EMAILS_PER_DAY=50

# Logging
LOG_LEVEL=INFO
EOF
    echo "Created .env template - please fill in your API keys"
fi

# Initialize database
echo "Initializing database..."
python3 -m src.db.migrate

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Fill in your API keys in .env file"
echo "2. Set up PostgreSQL database"
echo "3. Run: source venv/bin/activate"
echo "4. Run: python -m src.main find-leads --location 'Austin, TX' --count 10"