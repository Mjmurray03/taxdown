"""
Audit logging middleware for tracking data modifications.

Logs all CREATE, UPDATE, DELETE operations with user context,
timestamps, and change details for compliance and debugging.
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


# Configure audit logger
audit_logger = logging.getLogger("taxdown.audit")
audit_logger.setLevel(logging.INFO)

# Create a separate handler for audit logs if not already configured
if not audit_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - AUDIT - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    audit_logger.addHandler(handler)
    audit_logger.propagate = False


class AuditAction(str, Enum):
    """Types of auditable actions."""
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    EXPORT = "EXPORT"
    IMPORT = "IMPORT"
    ANALYZE = "ANALYZE"
    GENERATE = "GENERATE"


class AuditStatus(str, Enum):
    """Outcome status of an audited action."""
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    DENIED = "DENIED"
    ERROR = "ERROR"


@dataclass
class AuditEntry:
    """
    Structured audit log entry.

    Contains all information needed for compliance auditing
    and security incident investigation.
    """
    # Identifiers
    audit_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    request_id: Optional[str] = None

    # Timestamp
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Actor information
    actor_type: str = "api_key"  # api_key, user, system, anonymous
    actor_id: Optional[str] = None
    actor_ip: Optional[str] = None
    actor_user_agent: Optional[str] = None

    # Action details
    action: AuditAction = AuditAction.READ
    resource_type: str = ""  # e.g., "portfolio", "property", "user"
    resource_id: Optional[str] = None
    resource_name: Optional[str] = None

    # Request details
    method: str = ""
    path: str = ""
    query_params: Optional[dict] = None

    # Outcome
    status: AuditStatus = AuditStatus.SUCCESS
    status_code: int = 200
    error_message: Optional[str] = None

    # Performance
    duration_ms: Optional[float] = None

    # Change tracking (for updates)
    changes: Optional[dict] = None  # {"field": {"old": x, "new": y}}

    def to_dict(self) -> dict:
        """Convert to dictionary for logging/storage."""
        return {
            "audit_id": self.audit_id,
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat(),
            "actor": {
                "type": self.actor_type,
                "id": self.actor_id,
                "ip": self.actor_ip,
                "user_agent": self.actor_user_agent,
            },
            "action": self.action.value,
            "resource": {
                "type": self.resource_type,
                "id": self.resource_id,
                "name": self.resource_name,
            },
            "request": {
                "method": self.method,
                "path": self.path,
                "query_params": self.query_params,
            },
            "outcome": {
                "status": self.status.value,
                "status_code": self.status_code,
                "error": self.error_message,
            },
            "duration_ms": self.duration_ms,
            "changes": self.changes,
        }

    def to_json(self) -> str:
        """Convert to JSON string for logging."""
        return json.dumps(self.to_dict(), default=str)


class AuditLogger:
    """
    Service for creating and storing audit logs.

    Can be extended to write to database, external services,
    or log aggregation systems.
    """

    # HTTP methods that modify data
    WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    # Map HTTP methods to audit actions
    METHOD_TO_ACTION = {
        "POST": AuditAction.CREATE,
        "PUT": AuditAction.UPDATE,
        "PATCH": AuditAction.UPDATE,
        "DELETE": AuditAction.DELETE,
        "GET": AuditAction.READ,
    }

    # Resource type mapping from URL paths
    RESOURCE_PATTERNS = {
        "/portfolios": "portfolio",
        "/properties": "property",
        "/users": "user",
        "/analysis": "analysis",
        "/appeals": "appeal",
        "/reports": "report",
    }

    def __init__(
        self,
        log_reads: bool = False,
        log_to_database: bool = False,
        sensitive_fields: Optional[set] = None,
    ):
        """
        Initialize audit logger.

        Args:
            log_reads: Whether to log GET requests (can be noisy)
            log_to_database: Whether to persist logs to database
            sensitive_fields: Field names to redact from logs
        """
        self.log_reads = log_reads
        self.log_to_database = log_to_database
        self.sensitive_fields = sensitive_fields or {
            "password", "api_key", "token", "secret", "ssn"
        }

    def should_log(self, method: str, path: str) -> bool:
        """Determine if this request should be audited."""
        # Always log write operations
        if method in self.WRITE_METHODS:
            return True

        # Optionally log reads
        if method == "GET" and self.log_reads:
            return True

        # Skip health checks and docs
        skip_paths = ["/health", "/docs", "/redoc", "/openapi.json", "/"]
        if any(path.startswith(p) or path == p for p in skip_paths):
            return False

        return False

    def extract_resource_info(self, path: str) -> tuple[str, Optional[str]]:
        """
        Extract resource type and ID from URL path.

        Returns:
            Tuple of (resource_type, resource_id)
        """
        resource_type = "unknown"
        resource_id = None

        # Find matching resource pattern
        for pattern, rtype in self.RESOURCE_PATTERNS.items():
            if pattern in path:
                resource_type = rtype
                # Extract ID from path (assumes /resource/{id} pattern)
                parts = path.split(pattern)
                if len(parts) > 1:
                    id_part = parts[1].strip("/").split("/")[0]
                    if id_part and id_part != "":
                        resource_id = id_part
                break

        return resource_type, resource_id

    def extract_actor_info(self, request: Request) -> dict:
        """Extract actor information from request."""
        # Get IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else None

        # Get API key info (truncated for security)
        api_key = request.headers.get("X-API-Key")
        actor_id = None
        actor_type = "anonymous"

        if api_key:
            actor_id = api_key[:16] + "..."  # Only log prefix
            actor_type = "api_key"

        return {
            "type": actor_type,
            "id": actor_id,
            "ip": ip,
            "user_agent": request.headers.get("User-Agent"),
        }

    def redact_sensitive(self, data: Any) -> Any:
        """Redact sensitive fields from data."""
        if isinstance(data, dict):
            return {
                k: "[REDACTED]" if k.lower() in self.sensitive_fields else self.redact_sensitive(v)
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [self.redact_sensitive(item) for item in data]
        return data

    def log(self, entry: AuditEntry) -> None:
        """
        Log an audit entry.

        Writes to configured destinations (logger, database, etc.)
        """
        # Always log to audit logger
        log_line = entry.to_json()

        if entry.status == AuditStatus.SUCCESS:
            audit_logger.info(log_line)
        elif entry.status == AuditStatus.DENIED:
            audit_logger.warning(log_line)
        else:
            audit_logger.error(log_line)

        # Optionally persist to database
        if self.log_to_database:
            self._persist_to_database(entry)

    def _persist_to_database(self, entry: AuditEntry) -> None:
        """
        Persist audit entry to database.

        This is a placeholder - implement based on your database setup.
        """
        # TODO: Implement database persistence
        # Example: INSERT INTO audit_logs (audit_id, ...) VALUES (...)
        pass

    def create_entry(
        self,
        request: Request,
        response: Response,
        duration_ms: float,
        error_message: Optional[str] = None,
    ) -> AuditEntry:
        """Create an audit entry from request/response."""
        actor_info = self.extract_actor_info(request)
        resource_type, resource_id = self.extract_resource_info(request.url.path)

        # Determine action
        action = self.METHOD_TO_ACTION.get(request.method, AuditAction.READ)

        # Determine status
        if response.status_code >= 500:
            status = AuditStatus.ERROR
        elif response.status_code == 403:
            status = AuditStatus.DENIED
        elif response.status_code >= 400:
            status = AuditStatus.FAILURE
        else:
            status = AuditStatus.SUCCESS

        return AuditEntry(
            request_id=getattr(request.state, "request_id", None),
            actor_type=actor_info["type"],
            actor_id=actor_info["id"],
            actor_ip=actor_info["ip"],
            actor_user_agent=actor_info["user_agent"],
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            method=request.method,
            path=request.url.path,
            query_params=dict(request.query_params) if request.query_params else None,
            status=status,
            status_code=response.status_code,
            error_message=error_message,
            duration_ms=duration_ms,
        )


class AuditMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for automatic audit logging.

    Logs all data modification requests (POST, PUT, PATCH, DELETE)
    with actor, resource, and outcome information.
    """

    def __init__(
        self,
        app,
        log_reads: bool = False,
        exclude_paths: Optional[list[str]] = None,
    ):
        super().__init__(app)
        self.audit_logger = AuditLogger(log_reads=log_reads)
        self.exclude_paths = exclude_paths or [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip excluded paths
        if any(request.url.path.startswith(p) for p in self.exclude_paths):
            return await call_next(request)

        # Check if we should log this request
        if not self.audit_logger.should_log(request.method, request.url.path):
            return await call_next(request)

        # Track timing
        start_time = time.time()
        error_message = None

        try:
            response = await call_next(request)
        except Exception as e:
            error_message = str(e)
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000

            # Create and log audit entry
            try:
                # Need to handle case where response wasn't created
                if 'response' not in locals():
                    from fastapi.responses import JSONResponse
                    response = JSONResponse(
                        status_code=500,
                        content={"detail": "Internal server error"}
                    )

                entry = self.audit_logger.create_entry(
                    request=request,
                    response=response,
                    duration_ms=duration_ms,
                    error_message=error_message,
                )
                self.audit_logger.log(entry)
            except Exception as log_error:
                # Don't let logging errors affect the response
                audit_logger.error(f"Failed to create audit log: {log_error}")

        return response


def log_action(
    action: AuditAction,
    resource_type: str,
    resource_id: Optional[str] = None,
    resource_name: Optional[str] = None,
    changes: Optional[dict] = None,
    actor_id: Optional[str] = None,
    status: AuditStatus = AuditStatus.SUCCESS,
    error_message: Optional[str] = None,
) -> None:
    """
    Manually log an audit action.

    Use this for logging actions that aren't captured by middleware,
    such as background jobs or internal service calls.

    Example:
        log_action(
            action=AuditAction.DELETE,
            resource_type="portfolio",
            resource_id="abc123",
            actor_id="system",
            status=AuditStatus.SUCCESS,
        )
    """
    entry = AuditEntry(
        actor_type="system" if actor_id == "system" else "api_key",
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
        changes=changes,
        status=status,
        error_message=error_message,
    )

    logger = AuditLogger()
    logger.log(entry)


def audit_changes(
    resource_type: str,
    resource_id: str,
    old_data: dict,
    new_data: dict,
    actor_id: Optional[str] = None,
) -> None:
    """
    Log data changes with before/after comparison.

    Useful for UPDATE operations where you want to track
    exactly what changed.

    Example:
        audit_changes(
            resource_type="portfolio",
            resource_id="abc123",
            old_data={"name": "Old Name", "description": "Old desc"},
            new_data={"name": "New Name", "description": "Old desc"},
            actor_id="user123",
        )
    """
    # Calculate changes
    changes = {}
    all_keys = set(old_data.keys()) | set(new_data.keys())

    for key in all_keys:
        old_val = old_data.get(key)
        new_val = new_data.get(key)
        if old_val != new_val:
            changes[key] = {"old": old_val, "new": new_val}

    if not changes:
        return  # No actual changes

    log_action(
        action=AuditAction.UPDATE,
        resource_type=resource_type,
        resource_id=resource_id,
        changes=changes,
        actor_id=actor_id,
        status=AuditStatus.SUCCESS,
    )
