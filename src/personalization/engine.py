"""Personalization engine using mimo-v2.5."""
from openai import AsyncOpenAI
from typing import Dict, Any, List
from config.settings import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL


class PersonalizationEngine:
    """Generate personalized messages using AI."""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL
        )
        self.model = OPENAI_MODEL

    async def generate_email(
        self,
        lead: Dict[str, Any],
        template: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, str]:
        """Generate a personalized email for a lead."""
        prompt = f"""You are a professional sales representative for a real estate lead generation service.

Generate a personalized cold email for this lead:
- Name: {lead.get('first_name', 'there')} {lead.get('last_name', '')}
- Company: {lead.get('company', 'their company')}
- Title: {lead.get('title', 'their position')}
- Location: {lead.get('location', 'their area')}
- Industry: {lead.get('industry', 'real estate')}

Context about our service:
{context or 'We help real estate agents find more clients through AI-powered lead generation.'}

Template to follow:
{template}

Requirements:
1. Keep it under 150 words
2. Use a conversational, friendly tone
3. Include a specific personalization based on their info
4. End with a clear call-to-action
5. Do NOT use generic phrases like "I hope this email finds you well"
6. Make it feel like it was written by a human, not a robot

Return ONLY the email content, no explanations."""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert email copywriter."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )

        content = response.choices[0].message.content

        # Generate subject line
        subject_prompt = f"""Generate a compelling email subject line for this email:
{content}

Requirements:
1. Under 50 characters
2. Personalized (use their name if possible)
3. Create curiosity or urgency
4. Do NOT use spam words like "free", "guarantee", etc.

Return ONLY the subject line, no quotes or explanations."""

        subject_response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert email subject line writer."},
                {"role": "user", "content": subject_prompt}
            ],
            temperature=0.8,
            max_tokens=100
        )

        subject = subject_response.choices[0].message.content.strip()

        return {
            "subject": subject,
            "body": content
        }

    async def generate_follow_up(
        self,
        lead: Dict[str, Any],
        previous_emails: List[Dict[str, Any]],
        step: int
    ) -> Dict[str, str]:
        """Generate a follow-up email."""
        history = "\n".join([
            f"Step {i+1} - Subject: {email.get('subject', 'N/A')}\n{email.get('body', 'N/A')}"
            for i, email in enumerate(previous_emails)
        ])

        prompt = f"""Generate follow-up email #{step} for this lead:

Lead Info:
- Name: {lead.get('first_name', 'there')} {lead.get('last_name', '')}
- Company: {lead.get('company', 'their company')}
- Title: {lead.get('title', 'their position')}

Previous emails sent:
{history}

Requirements:
1. Reference something from previous emails
2. Add new value (market insights, case study, etc.)
3. Keep under 100 words
4. Do NOT be pushy or desperate
5. End with a soft call-to-action
6. Vary the tone from previous emails

Return ONLY the email content, no explanations."""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert at writing follow-up emails."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=400
        )

        content = response.choices[0].message.content

        # Generate follow-up subject
        subject_prompt = f"""Generate a follow-up email subject line for step {step}:
{content}

Requirements:
1. Under 40 characters
2. Reference previous communication subtly
3. Create urgency without being pushy
4. Do NOT use "Following up" or similar

Return ONLY the subject line, no quotes or explanations."""

        subject_response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert email subject line writer."},
                {"role": "user", "content": subject_prompt}
            ],
            temperature=0.8,
            max_tokens=100
        )

        subject = subject_response.choices[0].message.content.strip()

        return {
            "subject": subject,
            "body": content
        }