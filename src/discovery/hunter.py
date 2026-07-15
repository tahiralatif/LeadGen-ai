"""Hunter.io lead discovery."""
import httpx
from typing import List, Dict, Any
from config.settings import HUNTER_API_KEY, HUNTER_BASE_URL


class HunterDiscovery:
    """Discover leads using Hunter.io API."""

    def __init__(self):
        self.api_key = HUNTER_API_KEY
        self.base_url = HUNTER_BASE_URL

    async def find_emails(self, domain: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Find email addresses for a domain."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/domain-search",
                params={
                    "api_key": self.api_key,
                    "domain": domain,
                    "limit": limit,
                    "type": "personal"
                }
            )
            response.raise_for_status()
            data = response.json()

        leads = []
        for email_data in data.get("data", {}).get("emails", []):
            lead = {
                "email": email_data.get("value"),
                "first_name": email_data.get("first_name"),
                "last_name": email_data.get("last_name"),
                "company": domain.split(".")[0].title(),
                "title": email_data.get("position"),
                "phone": email_data.get("phone_number"),
                "location": None,
                "source": "hunter",
                "linkedin_url": email_data.get("linkedin"),
                "confidence_score": email_data.get("confidence", 0)
            }
            if lead["email"] and lead["confidence_score"] >= 50:
                leads.append(lead)

        return leads

    async def verify_email(self, email: str) -> Dict[str, Any]:
        """Verify if an email address is valid."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/email-verifier",
                params={
                    "api_key": self.api_key,
                    "email": email
                }
            )
            response.raise_for_status()
            data = response.json()

        result = data.get("data", {})
        return {
            "email": email,
            "is_valid": result.get("result") == "valid",
            "score": result.get("score", 0),
            "status": result.get("result"),
            "reason": result.get("reason"),
            "disposable": result.get("disposable", False),
            "webmail": result.get("webmail", False)
        }

    async def find_by_name(self, name: str, company: str = None) -> List[Dict[str, Any]]:
        """Find email by name and company."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/email-finder",
                params={
                    "api_key": self.api_key,
                    "full_name": name,
                    "company": company or "",
                    "domain": f"{company.lower().replace(' ', '')}.com" if company else ""
                }
            )
            response.raise_for_status()
            data = response.json()

        results = []
        for item in data.get("data", []):
            results.append({
                "email": item.get("email"),
                "score": item.get("score", 0),
                "position": item.get("position")
            })

        return results