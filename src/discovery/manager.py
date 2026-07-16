"""Discovery manager to coordinate multiple sources with real email finding."""
from typing import List, Dict, Any
from .apollo import ApolloDiscovery
from .hunter import HunterDiscovery
from .scraper import CamoufoxScraper
from .email_finder import EmailFinder


class DiscoveryManager:
    """Manage lead discovery from multiple sources."""

    def __init__(self):
        self.apollo = ApolloDiscovery()
        self.hunter = HunterDiscovery()
        self.scraper = CamoufoxScraper()
        self.email_finder = EmailFinder()

    async def discover_leads(
        self,
        location: str = None,
        title: str = None,
        industry: str = None,
        company_domain: str = None,
        limit: int = 50,
        find_emails: bool = True
    ) -> List[Dict[str, Any]]:
        """Discover leads from multiple sources."""
        all_leads = []

        # Try Apollo API first
        try:
            apollo_leads = await self.apollo.search_people(
                location=location,
                title=title,
                industry=industry,
                limit=limit
            )
            all_leads.extend(apollo_leads)
        except Exception as e:
            print(f"Apollo API failed (expected on free plan): {e}")
            print("Falling back to web scraping...")

        # If API failed or returned empty, use scraper
        if not all_leads:
            try:
                print("Scraping Google Maps...")
                scraper_leads = self.scraper.scrape_google_maps(
                    query=title or "real estate agents",
                    location=location or "Austin, TX",
                    limit=limit
                )
                all_leads.extend(scraper_leads)
            except Exception as e:
                print(f"Google Maps scraping failed: {e}")

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

        # Find real emails for all leads
        if find_emails and all_leads:
            all_leads = await self.scraper.find_emails_for_leads(all_leads)

        # Deduplicate by email or company name
        seen = set()
        unique_leads = []
        for lead in all_leads:
            key = lead.get("email") or lead.get("company", "").lower()
            if key and key not in seen:
                seen.add(key)
                unique_leads.append(lead)

        return unique_leads[:limit]

    async def enrich_lead(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich lead with additional data."""
        # Try to find more info using Apollo
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

        # Find email if not present
        if not lead.get("email") and lead.get("company"):
            try:
                lead = await self.email_finder.find_emails_for_lead(lead)
            except Exception:
                pass

        return lead