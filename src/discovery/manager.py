"""Discovery manager to coordinate multiple sources."""
from typing import List, Dict, Any
from .apollo import ApolloDiscovery
from .hunter import HunterDiscovery


class DiscoveryManager:
    """Manage lead discovery from multiple sources."""

    def __init__(self):
        self.apollo = ApolloDiscovery()
        self.hunter = HunterDiscovery()

    async def discover_leads(
        self,
        location: str = None,
        title: str = None,
        industry: str = None,
        company_domain: str = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Discover leads from multiple sources."""
        all_leads = []

        # Apollo search
        try:
            apollo_leads = await self.apollo.search_people(
                location=location,
                title=title,
                industry=industry,
                limit=limit
            )
            all_leads.extend(apollo_leads)
        except Exception as e:
            print(f"Apollo search failed: {e}")

        # Hunter domain search
        if company_domain:
            try:
                hunter_leads = await self.hunter.find_emails(
                    domain=company_domain,
                    limit=limit
                )
                all_leads.extend(hunter_leads)
            except Exception as e:
                print(f"Hunter search failed: {e}")

        # Deduplicate by email
        seen_emails = set()
        unique_leads = []
        for lead in all_leads:
            if lead["email"] and lead["email"] not in seen_emails:
                seen_emails.add(lead["email"])
                unique_leads.append(lead)

        return unique_leads[:limit]

    async def enrich_lead(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich lead with additional data."""
        # Try to find more info using Hunter
        if lead.get("company"):
            try:
                domain = f"{lead['company'].lower().replace(' ', '')}.com"
                org_info = await self.apollo.get_organization(domain)
                lead.update({
                    "industry": org_info.get("industry"),
                    "company_size": org_info.get("employees"),
                    "company_description": org_info.get("description")
                })
            except Exception:
                pass

        return lead