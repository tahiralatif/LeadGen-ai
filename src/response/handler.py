"""Response handler for processing email replies."""
import imaplib
import email
from email.header import decode_header
from typing import List, Dict, Any
from openai import AsyncOpenAI
from config.settings import (
    OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL,
    EMAIL_FROM
)


class ResponseHandler:
    """Handle incoming email responses and classify intent."""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL
        )
        self.model = OPENAI_MODEL

    async def check_inbox(
        self,
        imap_host: str,
        imap_port: int,
        username: str,
        password: str,
        folder: str = "INBOX"
    ) -> List[Dict[str, Any]]:
        """Check inbox for new responses."""
        responses = []

        try:
            # Connect to IMAP
            mail = imaplib.IMAP4_SSL(imap_host, imap_port)
            mail.login(username, password)
            mail.select(folder)

            # Search for unread emails
            status, messages = mail.search(None, "UNSEEN")
            if status != "OK":
                return []

            for msg_num in messages[0].split():
                status, msg_data = mail.fetch(msg_num, "(RFC822)")
                if status != "OK":
                    continue

                msg = email.message_from_bytes(msg_data[0][1])

                # Skip emails from ourselves
                from_email = msg.get("From", "")
                if EMAIL_FROM in from_email:
                    continue

                # Get subject
                subject = ""
                if msg["Subject"]:
                    decoded = decode_header(msg["Subject"])
                    for part, encoding in decoded:
                        if isinstance(part, bytes):
                            subject += part.decode(encoding or "utf-8")
                        else:
                            subject += part

                # Get body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode()
                            break
                else:
                    body = msg.get_payload(decode=True).decode()

                responses.append({
                    "from": from_email,
                    "subject": subject,
                    "body": body,
                    "date": msg.get("Date")
                })

            mail.logout()

        except Exception as e:
            print(f"Inbox check failed: {e}")

        return responses

    async def classify_intent(self, email_content: str) -> Dict[str, Any]:
        """Classify the intent of an email response."""
        prompt = f"""Analyze this email response and classify its intent.

Email content:
{email_content}

Classify into ONE of these categories:
1. interested - Person wants to learn more or schedule a meeting
2. not_interested - Person explicitly declines
3. schedule - Person wants to schedule a meeting/call
4. question - Person has questions about the service
5. unsubscribe - Person wants to be removed from mailing list
6. spam - This is spam or auto-reply

Also analyze sentiment (positive, neutral, negative) and extract any key information (proposed meeting times, questions asked, etc.).

Return in JSON format:
{{
    "intent": "category",
    "sentiment": "positive/neutral/negative",
    "key_info": "any important details",
    "auto_reply_needed": true/false,
    "suggested_response": "suggested reply if auto-reply is needed"
}}"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert at analyzing email responses."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )

        import json
        content = response.choices[0].message.content
        try:
            # Try to parse as JSON
            result = json.loads(content)
        except json.JSONDecodeError:
            # If not valid JSON, extract manually
            result = {
                "intent": "question",
                "sentiment": "neutral",
                "key_info": content,
                "auto_reply_needed": True,
                "suggested_response": "Thank you for your response. We'll get back to you shortly."
            }

        return result

    async def generate_response(
        self,
        email_content: str,
        intent: str,
        lead_info: Dict[str, Any]
    ) -> str:
        """Generate an appropriate response based on intent."""
        prompts = {
            "interested": f"""Generate a response to express gratitude and propose next steps.
Lead: {lead_info.get('first_name', 'there')}
Email: {email_content}
Make it friendly and professional. Suggest scheduling a 15-minute demo call.""",

            "schedule": f"""Generate a response to schedule a meeting.
Lead: {lead_info.get('first_name', 'there')}
Email: {email_content}
Ask for their preferred time and provide a scheduling link or suggest specific times.""",

            "question": f"""Generate a response to answer their question.
Lead: {lead_info.get('first_name', 'there')}
Email: {email_content}
Answer their question professionally and offer additional help.""",

            "not_interested": f"""Generate a polite response acknowledging their decision.
Lead: {lead_info.get('first_name', 'there')}
Email: {email_content}
Thank them and leave the door open for future contact.""",

            "unsubscribe": f"""Generate a response confirming unsubscription.
Lead: {lead_info.get('first_name', 'there')}
Email: {email_content}
Confirm they've been unsubscribed and apologize for any inconvenience."""
        }

        prompt = prompts.get(intent, prompts["question"])

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a professional email responder."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=400
        )

        return response.choices[0].message.content