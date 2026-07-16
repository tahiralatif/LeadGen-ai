"""Error handling middleware."""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import traceback
from datetime import datetime


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Global error handling middleware."""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response

        except HTTPException as e:
            # Handle HTTP exceptions
            logger.warning(f"HTTP {e.status_code}: {e.detail} - {request.url.path}")
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "success": False,
                    "error": e.detail,
                    "status_code": e.status_code
                }
            )

        except Exception as e:
            # Handle unexpected errors
            error_id = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            logger.error(f"Unhandled error [{error_id}]: {str(e)} - {request.url.path}")
            logger.error(traceback.format_exc())

            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": "Internal server error",
                    "error_id": error_id,
                    "detail": str(e) if logger.isEnabledFor(logging.DEBUG) else None
                }
            )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Request logging middleware."""

    async def dispatch(self, request: Request, call_next):
        start_time = datetime.utcnow()

        # Log request
        logger.info(f"→ {request.method} {request.url.path}")

        response = await call_next(request)

        # Calculate duration
        duration = (datetime.utcnow() - start_time).total_seconds() * 1000

        # Log response
        logger.info(f"← {response.status_code} {request.url.path} ({duration:.0f}ms)")

        return response