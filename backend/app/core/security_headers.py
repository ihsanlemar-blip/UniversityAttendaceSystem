"""Security response headers and sensitive cache control middleware.

Enforces:
- X-Content-Type-Options: nosniff (MIME-type sniffing defense)
- X-Frame-Options: DENY & CSP frame-ancestors: 'none' (anti-clickjacking)
- Referrer-Policy: strict-origin-when-cross-origin
- Permissions-Policy: restricted camera, microphone, geolocation, bluetooth
- Strict-Transport-Security (HSTS) in production environment / HTTPS
- Cache-Control: no-store, no-cache, private on sensitive API routes
"""

from collections.abc import Callable

from backend.app.core.config import get_settings
from backend.app.core.constants import Environment
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware applying OWASP-recommended security and anti-caching headers."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response: Response = await call_next(request)
        settings = get_settings()

        # 1. Base Anti-MIME-Sniffing & Clickjacking Defense
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(self), microphone=(), geolocation=(), bluetooth=(self)"
        )

        # 2. Content Security Policy for API Responses
        if "Content-Security-Policy" not in response.headers:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self';"
            )

        # 3. HTTP Strict Transport Security (HSTS) - Production or HTTPS only
        is_https = (
            request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
        )
        if (
            settings.APP_ENV == Environment.PRODUCTION or is_https
        ) and "Strict-Transport-Security" not in response.headers:
            # 1 year max-age with includeSubDomains
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # 4. Sensitive API Cache Control (never publicly cache sensitive data)
        path = request.url.path
        if path.startswith("/api/") or path.startswith("/auth/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"

        return response
