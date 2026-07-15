"""Email verification using Hunter.io (free tier)."""
import httpx
from typing import Dict, Any, List
from config.settings import HUNTER_API_KEY


class EmailVerifier:
    """Verify email addresses for deliverability."""

    def __init__(self):
        self.api_key = HUNTER_API_KEY

    async def verify_email(self, email: str) -> Dict[str, Any]:
        """Verify a single email address using Hunter.io."""
        if not self.api_key or self.api_key == "skipped_for_now":
            # Return basic verification if no API key
            return {
                "email": email,
                "verified": True,  # Assume valid
                "score": 75,
                "status": "assumed_valid",
                "reason": "no_api_key",
                "sub_status": None
            }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    'https://api.hunter.io/v2/email-verifier',
                    params={
                        'api_key': self.api_key,
                        'email': email
                    }
                )
                response.raise_for_status()
                data = response.json().get('data', {})

            status = data.get('status', 'unknown')
            
            # Map Hunter status to our verification result
            status_map = {
                "valid": {"verified": True, "score": 100, "reason": None},
                "catchall": {"verified": True, "score": 80, "reason": "catch_all"},
                "invalid": {"verified": False, "score": 0, "reason": data.get('disposable', False) and 'disposable' or 'invalid'},
                "disposable": {"verified": False, "score": 0, "reason": "disposable"},
                "unknown": {"verified": False, "score": 50, "reason": "unknown"}
            }

            mapped = status_map.get(status, status_map["unknown"])

            return {
                "email": email,
                "verified": mapped["verified"],
                "score": mapped["score"],
                "status": status,
                "reason": mapped["reason"],
                "sub_status": None
            }
        except Exception as e:
            # If API fails, assume valid
            return {
                "email": email,
                "verified": True,
                "score": 75,
                "status": "api_error",
                "reason": str(e),
                "sub_status": None
            }

    async def verify_batch(self, emails: List[str]) -> List[Dict[str, Any]]:
        """Verify multiple email addresses."""
        results = []
        for email in emails:
            try:
                result = await self.verify_email(email)
                results.append(result)
            except Exception as e:
                results.append({
                    "email": email,
                    "verified": False,
                    "score": 0,
                    "status": "error",
                    "reason": str(e)
                })
        return results

    def is_safe_to_send(self, verification_result: Dict[str, Any], min_score: int = 70) -> bool:
        """Check if email is safe to send to."""
        return (
            verification_result["verified"] and
            verification_result["score"] >= min_score
        )