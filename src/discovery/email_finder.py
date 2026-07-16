"""Real email finder - scrapes websites and guesses patterns."""
import re
import httpx
import asyncio
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup


class EmailFinder:
    """Find real email addresses from websites."""

    # Common email patterns
    COMMON_PATTERNS = [
        "info@{domain}",
        "contact@{domain}",
        "hello@{domain}",
        "admin@{domain}",
        "office@{domain}",
        "support@{domain}",
        "sales@{domain}",
        "marketing@{domain}",
    ]

    # Email regex
    EMAIL_REGEX = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

    # Common domains to skip
    SKIP_DOMAINS = [
        'example.com', 'gmail.com', 'yahoo.com', 'hotmail.com',
        'outlook.com', 'aol.com', 'icloud.com', 'mail.com',
        'protonmail.com', 'zoho.com', 'yandex.com'
    ]

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }

    async def find_emails_from_website(self, url: str) -> List[Dict[str, Any]]:
        """Scrape a website for email addresses."""
        emails_found = []

        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                response = await client.get(url, headers=self.headers)

                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')

                    # Find emails in text
                    text = soup.get_text()
                    emails = re.findall(self.EMAIL_REGEX, text)

                    # Find emails in mailto links
                    for link in soup.find_all('a', href=True):
                        if 'mailto:' in link['href']:
                            email = link['href'].replace('mailto:', '').split('?')[0].strip()
                            if '@' in email:
                                emails.append(email)

                    # Find emails in HTML attributes
                    for tag in soup.find_all(True, attrs={'href': True}):
                        if 'mailto:' in tag.get('href', ''):
                            email = tag['href'].replace('mailto:', '').split('?')[0].strip()
                            if '@' in email:
                                emails.append(email)

                    # Clean and deduplicate
                    seen = set()
                    for email in emails:
                        email = email.lower().strip()
                        if email not in seen and not self._is_personal_email(email):
                            seen.add(email)
                            emails_found.append({
                                'email': email,
                                'source': 'website',
                                'url': url
                            })

        except Exception as e:
            pass

        return emails_found

    async def find_emails_from_contact_page(self, domain: str) -> List[Dict[str, Any]]:
        """Try to find emails from contact page."""
        contact_urls = [
            f"https://www.{domain}/contact",
            f"https://www.{domain}/contact-us",
            f"https://www.{domain}/contact.html",
            f"https://www.{domain}/about",
            f"https://www.{domain}/about-us",
            f"https://{domain}/contact",
            f"https://{domain}/contact-us",
        ]

        all_emails = []

        for url in contact_urls:
            try:
                emails = await self.find_emails_from_website(url)
                all_emails.extend(emails)
                if emails:
                    break  # Found emails, stop trying
            except:
                continue

        return all_emails

    def guess_email_patterns(self, domain: str, first_name: str = None, last_name: str = None) -> List[Dict[str, Any]]:
        """Guess common email patterns."""
        guessed = []

        # Common generic emails
        for pattern in self.COMMON_PATTERNS:
            email = pattern.format(domain=domain)
            guessed.append({
                'email': email,
                'source': 'pattern_guess',
                'confidence': 60
            })

        # If we have name, try name patterns
        if first_name and last_name:
            name_patterns = [
                f"{first_name.lower()}@{domain}",
                f"{first_name.lower()}.{last_name.lower()}@{domain}",
                f"{first_name.lower()[0]}{last_name.lower()}@{domain}",
                f"{first_name.lower()}{last_name.lower()[0]}@{domain}",
                f"{first_name.lower()}_{last_name.lower()}@{domain}",
            ]
            for email in name_patterns:
                guessed.append({
                    'email': email,
                    'source': 'name_pattern',
                    'confidence': 70
                })

        return guessed

    async def find_emails_for_lead(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        """Find emails for a single lead."""
        company = lead.get('company', '')
        domain = self._company_to_domain(company)

        if not domain:
            return lead

        # Try to find real emails
        all_emails = []

        # 1. Try contact page
        contact_emails = await self.find_emails_from_contact_page(domain)
        all_emails.extend(contact_emails)

        # 2. Try main website
        if not all_emails:
            main_emails = await self.find_emails_from_website(f"https://www.{domain}")
            all_emails.extend(main_emails)

        # 3. Guess patterns
        guessed = self.guess_email_patterns(
            domain,
            lead.get('first_name'),
            lead.get('last_name')
        )
        all_emails.extend(guessed)

        # Pick best email
        if all_emails:
            # Prefer real emails over guessed
            real_emails = [e for e in all_emails if e['source'] != 'pattern_guess']
            if real_emails:
                lead['email'] = real_emails[0]['email']
                lead['email_source'] = real_emails[0]['source']
            else:
                lead['email'] = all_emails[0]['email']
                lead['email_source'] = 'guessed'
            lead['email_confidence'] = all_emails[0].get('confidence', 90)
        else:
            lead['email'] = None
            lead['email_source'] = 'not_found'

        return lead

    async def find_emails_for_leads(self, leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find emails for multiple leads."""
        tasks = [self.find_emails_for_lead(lead) for lead in leads]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        enriched_leads = []
        for result in results:
            if isinstance(result, dict):
                enriched_leads.append(result)

        return enriched_leads

    def _company_to_domain(self, company: str) -> Optional[str]:
        """Convert company name to domain."""
        if not company:
            return None

        # Clean company name
        clean = company.lower()
        clean = re.sub(r'[^a-z0-9\s]', '', clean)
        clean = re.sub(r'\s+', '', clean)

        # Try common TLDs
        tlds = ['.com', '.io', '.co', '.net', '.org']
        for tld in tlds:
            domain = clean + tld
            if domain not in self.SKIP_DOMAINS:
                return domain

        return clean + '.com'

    def _is_personal_email(self, email: str) -> bool:
        """Check if email is personal (gmail, etc.)."""
        personal_domains = [
            'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
            'aol.com', 'icloud.com', 'mail.com', 'protonmail.com'
        ]
        domain = email.split('@')[1] if '@' in email else ''
        return domain.lower() in personal_domains


# Create instance
email_finder = EmailFinder()