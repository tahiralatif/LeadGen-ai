"""Web scraping using Camoufox for lead discovery."""
import asyncio
import json
from typing import List, Dict, Any
from camoufox.sync_api import Camoufox


class CamoufoxScraper:
    """Scrape leads using Camoufox browser automation."""

    def __init__(self):
        self.browser = None

    def scrape_apollo_web(
        self,
        location: str = None,
        title: str = None,
        limit: int = 25
    ) -> List[Dict[str, Any]]:
        """Scrape Apollo.io website for leads."""
        leads = []
        
        # Build search URL
        search_terms = []
        if title:
            search_terms.append(title)
        if location:
            search_terms.append(location)
        
        search_query = " ".join(search_terms) if search_terms else "real estate agent"
        url = f"https://app.apollo.io/#/people?search={search_query.replace(' ', '%20')}"
        
        print(f"Scraping: {url}")
        
        with Camoufox(headless=True) as browser:
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Wait for results to load
            page.wait_for_selector('[data-testid="person-row"]', timeout=10000)
            
            # Extract leads
            rows = page.query_selector_all('[data-testid="person-row"]')
            
            for row in rows[:limit]:
                try:
                    # Extract name
                    name_el = row.query_selector('[data-testid="person-name"]')
                    name = name_el.inner_text() if name_el else ""
                    
                    # Extract title
                    title_el = row.query_selector('[data-testid="person-title"]')
                    title_text = title_el.inner_text() if title_el else ""
                    
                    # Extract company
                    company_el = row.query_selector('[data-testid="person-company"]')
                    company = company_el.inner_text() if company_el else ""
                    
                    # Extract email (may be hidden)
                    email_el = row.query_selector('[data-testid="person-email"]')
                    email = email_el.inner_text() if email_el else None
                    
                    # Extract location
                    location_el = row.query_selector('[data-testid="person-location"]')
                    location_text = location_el.inner_text() if location_el else ""
                    
                    lead = {
                        "first_name": name.split()[0] if name else "",
                        "last_name": " ".join(name.split()[1:]) if name else "",
                        "title": title_text,
                        "company": company,
                        "email": email,
                        "location": location_text,
                        "source": "apollo_web"
                    }
                    
                    if lead["first_name"] or lead["company"]:
                        leads.append(lead)
                        
                except Exception as e:
                    print(f"Error extracting row: {e}")
                    continue
        
        return leads

    def scrape_google_maps(
        self,
        query: str = "real estate agents",
        location: str = "Austin, TX",
        limit: int = 25
    ) -> List[Dict[str, Any]]:
        """Scrape Google Maps for business leads."""
        leads = []
        search_query = f"{query} in {location}"
        url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"
        
        print(f"Scraping: {url}")
        
        with Camoufox(headless=True) as browser:
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Wait for results
            page.wait_for_selector('[class*="Nv2PK"]', timeout=10000)
            
            # Extract business listings
            listings = page.query_selector_all('[class*="Nv2PK"]')
            
            for listing in listings[:limit]:
                try:
                    # Extract name
                    name_el = listing.query_selector('[class*="qBF1Pd"]')
                    name = name_el.inner_text() if name_el else ""
                    
                    # Extract category/type
                    type_el = listing.query_selector('[class*="W4Efsd"]')
                    biz_type = type_el.inner_text() if type_el else ""
                    
                    # Extract rating
                    rating_el = listing.query_selector('[class*="MW4etd"]')
                    rating = rating_el.inner_text() if rating_el else ""
                    
                    # Extract address
                    addr_el = listing.query_selector('[class*="W4Efsd"]:last-child')
                    address = addr_el.inner_text() if addr_el else ""
                    
                    lead = {
                        "company": name,
                        "title": biz_type,
                        "location": address,
                        "rating": rating,
                        "source": "google_maps"
                    }
                    
                    if lead["company"]:
                        leads.append(lead)
                        
                except Exception as e:
                    print(f"Error extracting listing: {e}")
                    continue
        
        return leads

    def scrape_linkedin_web(
        self,
        query: str = "real estate agent",
        location: str = "Austin, TX",
        limit: int = 25
    ) -> List[Dict[str, Any]]:
        """Scrape LinkedIn search results (public)."""
        leads = []
        search_query = f"{query} {location}"
        url = f"https://www.linkedin.com/search/results/people/?keywords={search_query.replace(' ', '%20')}"
        
        print(f"Scraping: {url}")
        
        with Camoufox(headless=True) as browser:
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Wait for results
            page.wait_for_selector('[class*="reusable-search__result-container"]', timeout=10000)
            
            # Extract profiles
            profiles = page.query_selector_all('[class*="reusable-search__result-container"]')
            
            for profile in profiles[:limit]:
                try:
                    # Extract name
                    name_el = profile.query_selector('[class*="entity-result__title-text"]')
                    name = name_el.inner_text() if name_el else ""
                    
                    # Extract title
                    title_el = profile.query_selector('[class*="entity-result__primary-subtitle"]')
                    title_text = title_el.inner_text() if title_el else ""
                    
                    # Extract location
                    location_el = profile.query_selector('[class*="entity-result__secondary-subtitle"]')
                    location_text = location_el.inner_text() if location_el else ""
                    
                    # Extract profile link
                    link_el = profile.query_selector('a[href*="/in/"]')
                    linkedin_url = link_el.get_attribute('href') if link_el else ""
                    
                    lead = {
                        "first_name": name.split()[0] if name else "",
                        "last_name": " ".join(name.split()[1:]) if name else "",
                        "title": title_text,
                        "location": location_text,
                        "linkedin_url": linkedin_url,
                        "source": "linkedin"
                    }
                    
                    if lead["first_name"]:
                        leads.append(lead)
                        
                except Exception as e:
                    print(f"Error extracting profile: {e}")
                    continue
        
        return leads


# Create instance
scraper = CamoufoxScraper()