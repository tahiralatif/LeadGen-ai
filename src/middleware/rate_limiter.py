"""Rate limiting middleware."""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
import time
from typing import Dict, Tuple


class RateLimiter:
    """In-memory rate limiter."""

    def __init__(self):
        self.requests: Dict[str, list] = defaultdict(list)

    def is_rate_limited(self, key: str, max_requests: int = 60, window_seconds: int = 60) -> bool:
        """Check if request is rate limited."""
        now = time.time()
        window_start = now - window_seconds

        # Remove old requests
        self.requests[key] = [t for t in self.requests[key] if t > window_start]

        # Check if rate limited
        if len(self.requests[key]) >= max_requests:
            return True

        # Add new request
        self.requests[key].append(now)
        return False

    def get_remaining(self, key: str, max_requests: int = 60, window_seconds: int = 60) -> int:
        """Get remaining requests."""
        now = time.time()
        window_start = now - window_seconds

        # Remove old requests
        self.requests[key] = [t for t in self.requests[key] if t > window_start]

        return max(0, max_requests - len(self.requests[key]))


# Global rate limiter instance
rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware for FastAPI."""

    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Create rate limit key
        key = f"{client_ip}:{request.url.path}"

        # Check rate limit (skip for health check)
        if request.url.path != "/health":
            if rate_limiter.is_rate_limited(key, self.max_requests, self.window_seconds):
                return JSONResponse(
                    status_code=429,
                    content={
                        "success": False,
                        "error": "Rate limit exceeded. Please try again later.",
                        "retry_after": self.window_seconds
                    }
                )

        # Add rate limit headers
        response = await call_next(request)
        remaining = rate_limiter.get_remaining(key, self.max_requests, self.window_seconds)
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response