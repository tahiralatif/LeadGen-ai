"""Email verification using ZeroBounce and Hunter."""
import httpx
from typing import Dict, Any, List
from config.settings import ZEROBOUNCE_API_KEY, ZEROBOUNCE_BASE_URL


class EmailVerifier:
    """Verify email addresses for deliverability."""

    def __init__(self):
        self.api_key = ZEROBOUNCE_API_KEY

    async def verify_email(self, email: str) -> Dict[str, Any]:
        """Verify a single email address."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{ZEROBOUNCE_BASE_URL}/verify",
                params={
                    "api_key": self.api_key,
                    "email": email
                }
            )
            response.raise_for_status()
            data = response.json()

        result = data.get("status", "unknown")

        # Map ZeroBounce status to our verification result
        status_map = {
            "valid": {"verified": True, "score": 100, "reason": None},
            "catch-all": {"verified": True, "score": 80, "reason": "catch_all"},
            "invalid": {"verified": False, "score": 0, "reason": data.get("sub_status", "invalid")},
            "disposable": {"verified": False, "score": 0, "reason": "disposable"},
            "unknown": {"verified": False, "score": 50, "reason": "unknown"},
            "spamtrap": {"verified": False, "score": 0, "reason": "spamtrap"},
            "abuse": {"verified": False, "score": 0, "reason": "abuse"},
            "do_not_mail": {"verified": False, "score": 0, "reason": "do_not_mail"}
        }

        mapped = status_map.get(result, status_map["unknown"])

        return {
            "email": email,
            "verified": mapped["verified"],
            "score": mapped["score"],
            "status": result,
            "reason": mapped["reason"],
            "sub_status": data.get("sub_status")
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