#!/usr/bin/env python3
"""Quick test script for LeadGen Agent."""
import asyncio
import sys
from src.outreach.sender import EmailSender

async def test_email(to_email: str):
    """Send a test email."""
    sender = EmailSender()
    
    result = await sender.send_email(
        to_email=to_email,
        subject="Test from LeadGen Agent",
        html_content="""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2>Hello from LeadGen Agent!</h2>
            <p>This is a test email to verify your setup is working correctly.</p>
            <p>If you received this, your Brevo integration is working!</p>
            <br>
            <p>Best,<br>LeadGen Agent</p>
        </body>
        </html>
        """,
        plain_content="Hello from LeadGen Agent! This is a test email."
    )
    
    if result['success']:
        print(f"SUCCESS: Email sent to {to_email}")
        print(f"Message ID: {result['message_id']}")
    else:
        print(f"FAILED: {result['error']}")
    
    return result

if __name__ == "__main__":
    to_email = sys.argv[1] if len(sys.argv) > 1 else "tara378581@gmail.com"
    asyncio.run(test_email(to_email))