"""Apollo.io lead discovery."""
import httpx
from typing import List, Dict, Any
from config.settings import APOLLO_API_KEY, APOLLO_BASE_URL


class ApolloDiscovery:
    """Discover leads using Apollo.io API."""

    def __init__(self):
        self.api_key = APOLLO_API_KEY
        self.base_url = APOLLO_BASE_URL
        self.headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache"
        }

    async def search_people(
        self,
        location: str = None,
        title: str = None,
        industry: str = None,
        company_size: str = None,
        limit: int = 25
    ) -> List[Dict[str, Any]]:
        """Search for people matching criteria."""
        payload = {
            "api_key": self.api_key,
            "q_keywords": title or "real estate agent",
            "person_titles": [title] if title else ["Real Estate Agent", "Realtor"],
            "person_locations": [location] if location else [],
            "organization_industry_tag_ids": [],
            "per_page": min(limit, 100)
        }

        if industry:
            payload["organization_industry_tag_ids"] = [industry]

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/mixed_people/search",
                json=payload,
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()

        leads = []
        for person in data.get("people", []):
            lead = {
                "email": person.get("email"),
                "first_name": person.get("first_name"),
                "last_name": person.get("last_name"),
                "company": person.get("organization", {}).get("name"),
                "title": person.get("title"),
                "phone": person.get("phone_numbers", [{}])[0].get("sanitized_number") if person.get("phone_numbers") else None,
                "location": f"{person.get('city', '')}, {person.get('state', '')}",
                "source": "apollo",
                "linkedin_url": person.get("linkedin_url"),
                "confidence_score": person.get("email_confidence_score", 0)
            }
            if lead["email"]:
                leads.append(lead)

        return leads

    async def get_organization(self, domain: str) -> Dict[str, Any]:
        """Get organization details by domain."""
        payload = {
            "api_key": self.api_key,
            "domain": domain
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/organizations/search",
                json=payload,
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()

        org = data.get("organization", {})
        return {
            "name": org.get("name"),
            "domain": org.get("primary_domain"),
            "industry": org.get("industry"),
            "employees": org.get("estimated_num_employees"),
            "founded": org.get("founded_year"),
            "city": org.get("city"),
            "state": org.get("state"),
            "description": org.get("short_description")
        }