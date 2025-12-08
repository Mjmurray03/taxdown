"""
Secure headers middleware for HTTP response hardening.

Adds security headers to all responses to protect against
common web vulnerabilities like XSS, clickjacking, and MIME sniffing.
"""

from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.api.security import SecurityHeaders


class SecureHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security headers to all HTTP responses.

    Headers added:
    - X-Frame-Options: Prevent clickjacking
    - X-Content-Type-Options: Prevent MIME sniffing
    - X-XSS-Protection: XSS filter (legacy browsers)
    - Referrer-Policy: Control referrer information
    - Permissions-Policy: Restrict browser features
    - Content-Security-Policy: Control resource loading
    - Strict-Transport-Security: Force HTTPS (optional)
    - Cache-Control: Prevent caching of sensitive data
    """

    def __init__(
        self,
        app,
        include_hsts: bool = True,
        custom_csp: Optional[str] = None,
        exclude_paths: Optional[list[str]] = None,
    ):
        """
        Initialize secure headers middleware.

        Args:
            app: FastAPI application
            include_hsts: Include HSTS header (disable for local dev)
            custom_csp: Custom Content-Security-Policy (overrides default)
            exclude_paths: Paths to exclude from header injection
        """
        super().__init__(app)
        self.include_hsts = include_hsts
        self.custom_csp = custom_csp
        self.exclude_paths = exclude_paths or []

        # Pre-compute headers for performance
        self._headers = SecurityHeaders.get_headers(include_hsts=include_hsts)
        if custom_csp:
            self._headers["Content-Security-Policy"] = custom_csp

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Skip excluded paths (e.g., docs, static files)
        if any(request.url.path.startswith(p) for p in self.exclude_paths):
            return response

        # Add security headers
        for header, value in self._headers.items():
            # Don't override existing headers
            if header not in response.headers:
                response.headers[header] = value

        return response


class ContentSecurityPolicyBuilder:
    """
    Builder for constructing Content-Security-Policy headers.

    Provides a fluent interface for building CSP policies.
    """

    def __init__(self):
        self._directives = {}

    def default_src(self, *sources: str) -> "ContentSecurityPolicyBuilder":
        """Set default-src directive."""
        self._directives["default-src"] = sources
        return self

    def script_src(self, *sources: str) -> "ContentSecurityPolicyBuilder":
        """Set script-src directive."""
        self._directives["script-src"] = sources
        return self

    def style_src(self, *sources: str) -> "ContentSecurityPolicyBuilder":
        """Set style-src directive."""
        self._directives["style-src"] = sources
        return self

    def img_src(self, *sources: str) -> "ContentSecurityPolicyBuilder":
        """Set img-src directive."""
        self._directives["img-src"] = sources
        return self

    def font_src(self, *sources: str) -> "ContentSecurityPolicyBuilder":
        """Set font-src directive."""
        self._directives["font-src"] = sources
        return self

    def connect_src(self, *sources: str) -> "ContentSecurityPolicyBuilder":
        """Set connect-src directive (for API calls, WebSockets)."""
        self._directives["connect-src"] = sources
        return self

    def frame_src(self, *sources: str) -> "ContentSecurityPolicyBuilder":
        """Set frame-src directive."""
        self._directives["frame-src"] = sources
        return self

    def frame_ancestors(self, *sources: str) -> "ContentSecurityPolicyBuilder":
        """Set frame-ancestors directive (prevent embedding)."""
        self._directives["frame-ancestors"] = sources
        return self

    def base_uri(self, *sources: str) -> "ContentSecurityPolicyBuilder":
        """Set base-uri directive."""
        self._directives["base-uri"] = sources
        return self

    def form_action(self, *sources: str) -> "ContentSecurityPolicyBuilder":
        """Set form-action directive."""
        self._directives["form-action"] = sources
        return self

    def object_src(self, *sources: str) -> "ContentSecurityPolicyBuilder":
        """Set object-src directive (plugins)."""
        self._directives["object-src"] = sources
        return self

    def media_src(self, *sources: str) -> "ContentSecurityPolicyBuilder":
        """Set media-src directive (audio/video)."""
        self._directives["media-src"] = sources
        return self

    def upgrade_insecure_requests(self) -> "ContentSecurityPolicyBuilder":
        """Add upgrade-insecure-requests directive."""
        self._directives["upgrade-insecure-requests"] = ()
        return self

    def block_all_mixed_content(self) -> "ContentSecurityPolicyBuilder":
        """Add block-all-mixed-content directive."""
        self._directives["block-all-mixed-content"] = ()
        return self

    def report_uri(self, uri: str) -> "ContentSecurityPolicyBuilder":
        """Set report-uri for CSP violation reports."""
        self._directives["report-uri"] = (uri,)
        return self

    def build(self) -> str:
        """Build the CSP header value."""
        parts = []
        for directive, sources in self._directives.items():
            if sources:
                parts.append(f"{directive} {' '.join(sources)}")
            else:
                parts.append(directive)
        return "; ".join(parts)

    @classmethod
    def strict_api(cls) -> str:
        """
        Create a strict CSP policy for API-only applications.

        Blocks all content except self and specific API needs.
        """
        return (
            cls()
            .default_src("'none'")
            .frame_ancestors("'none'")
            .base_uri("'none'")
            .form_action("'none'")
            .upgrade_insecure_requests()
            .build()
        )

    @classmethod
    def standard_web_app(cls, api_domain: Optional[str] = None) -> str:
        """
        Create a standard CSP policy for web applications.

        Args:
            api_domain: Domain for API calls (e.g., 'api.example.com')
        """
        connect_sources = ["'self'"]
        if api_domain:
            connect_sources.append(f"https://{api_domain}")

        return (
            cls()
            .default_src("'self'")
            .script_src("'self'")
            .style_src("'self'", "'unsafe-inline'")
            .img_src("'self'", "data:", "https:")
            .font_src("'self'", "data:")
            .connect_src(*connect_sources)
            .frame_ancestors("'none'")
            .base_uri("'self'")
            .form_action("'self'")
            .upgrade_insecure_requests()
            .build()
        )


# Pre-built CSP policies for common use cases
CSP_STRICT_API = ContentSecurityPolicyBuilder.strict_api()
CSP_STANDARD_WEB = ContentSecurityPolicyBuilder.standard_web_app()
