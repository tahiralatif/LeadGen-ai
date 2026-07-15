"""Email verification using NeverBounce and Hunter."""
import httpx
from typing import Dict, Any, List
from config.settings import NEVERBOUNCE_API_KEY, NEVERBOUNCE_BASE_URL


class EmailVerifier:
    """Verify email addresses for deliverability."""

    def __init__(self):
        self.neverbounce_key = NEVERBOUNCE_API_KEY

    async def verify_email(self, email: str) -> Dict[str, Any]:
        """Verify a single email address."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{NEVERBOUNCE_BASE_URL}/verify",
                data={
                    "key": self.neverbounce_key,
                    "email": email
                }
            )
            response.raise_for_status()
            data = response.json()

        result = data.get("result", {})
        status = result.get("status", "unknown")

        # Map NeverBounce status to our verification result
        status_map = {
            "valid": {"verified": True, "score": 100, "reason": None},
            "valid_accept_all": {"verified": True, "score": 90, "reason": "accept_all"},
            "catchall": {"verified": True, "score": 80, "reason": "catch_all"},
            "invalid": {"verified": False, "score": 0, "reason": result.get("flags", [{}])[0] if result.get("flags") else "invalid"},
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
            "flags": result.get("flags", [])
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