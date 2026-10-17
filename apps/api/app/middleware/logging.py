import re
import time
import uuid
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("wapiflow.access")

# Regex to detect phone numbers for PII masking (never log phone numbers in full)
PHONE_REGEX = re.compile(r"(\+?[0-9]{1,4}[-.\s]?)?(\(?\d{2,4}\)?[-.\s]?)?[0-9]{3,4}[-.\s]?[0-9]{3,4}")


def mask_phone_number(text: str) -> str:
    """Mask phone numbers to preserve PII privacy."""
    def _replacer(match: re.Match) -> str:
        s = match.group(0).strip()
        if len(re.sub(r"\D", "", s)) >= 7:
            # Mask middle digits, leaving only first 2 and last 2 digits
            digits = re.sub(r"\D", "", s)
            prefix = digits[:2]
            suffix = digits[-2:]
            return f"{prefix}****{suffix}"
        return s

    return PHONE_REGEX.sub(_replacer, text)


class LoggingAndRequestIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that:
    1. Attaches a unique correlation ID (uuid4) to request.state.request_id and response header X-Request-ID.
    2. Logs structured request details with execution latency.
    3. Redacts phone numbers and sensitive headers to protect customer PII.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate or retain correlation ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.perf_counter()
        raw_url = str(request.url.path)
        masked_query = mask_phone_number(str(request.url.query)) if request.url.query else ""
        client_host = request.client.host if request.client else "unknown"

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000

            response.headers["X-Request-ID"] = request_id

            logger.info(
                f"[{request_id}] {request.method} {raw_url} - {response.status_code} "
                f"({duration_ms:.2f}ms) Client: {client_host} Query: {masked_query}"
            )
            return response
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"[{request_id}] {request.method} {raw_url} - FAILED ({duration_ms:.2f}ms) "
                f"Client: {client_host}: {str(exc)}"
            )
            raise
