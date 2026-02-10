"""
QMS MCP Server

Model Context Protocol server for the Quality Management System CLI.
Exposes QMS operations as MCP tools for integration with Claude Code and other MCP clients.

Requirements: REQ-MCP-001, REQ-MCP-002, REQ-MCP-011 through REQ-MCP-016
"""

import argparse
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from mcp.server.fastmcp import Context, FastMCP
from starlette.requests import Request

# Configure logging to stderr (CRITICAL: never write to stdout for stdio transport)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("qms-mcp")

# Initialize FastMCP server
mcp = FastMCP("qms")

# Known QMS agents (validated against .claude/agents/)
KNOWN_AGENTS = {"lead", "claude", "qa", "bu", "tu_ui", "tu_scene", "tu_sketch", "tu_sim"}


# ---------------------------------------------------------------------------
# Identity collision prevention (REQ-MCP-016)
# ---------------------------------------------------------------------------


class IdentityCollisionError(Exception):
    """Raised when an identity is locked by another instance."""

    pass


@dataclass
class IdentityLock:
    """Represents an active identity claim from an enforced-mode caller."""

    instance_id: str  # UUID from X-QMS-Instance header
    last_seen: float  # time.monotonic() timestamp
    identity: str  # The claimed identity (e.g., "qa")


# TTL for identity locks. After this duration without a heartbeat (HTTP request),
# the lock expires and the identity becomes available again. 5 minutes is long
# enough to span idle gaps between MCP calls but short enough for crash recovery.
IDENTITY_LOCK_TTL_SECONDS: float = 300.0

# In-memory registry mapping identity -> IdentityLock.
# Thread safety note: FastMCP with uvicorn uses a single event loop thread for
# request handling, so no mutex is needed. If multi-worker is ever enabled,
# a threading.Lock would be required here.
_identity_registry: dict[str, IdentityLock] = {}


def _cleanup_expired_locks() -> None:
    """Remove expired identity locks from the registry."""
    now = time.monotonic()
    expired = [
        identity
        for identity, lock in _identity_registry.items()
        if now - lock.last_seen > IDENTITY_LOCK_TTL_SECONDS
    ]
    for identity in expired:
        logger.info(f"Cleanup: expired identity lock for '{identity}'")
        del _identity_registry[identity]


def _register_identity(identity: str, instance_id: str) -> None:
    """Register an enforced-mode identity, detecting duplicate containers.

    Called on every HTTP identity resolution. Same instance_id refreshes the
    heartbeat. Different instance_id with a non-expired lock raises
    IdentityCollisionError (Scenario B: duplicate containers).

    Requirements: REQ-MCP-016
    """
    existing = _identity_registry.get(identity)
    if existing is not None:
        if existing.instance_id == instance_id:
            # Same instance (same container, subsequent request) -- heartbeat
            existing.last_seen = time.monotonic()
            return

        if time.monotonic() - existing.last_seen <= IDENTITY_LOCK_TTL_SECONDS:
            # Different instance, lock still active -- duplicate container
            raise IdentityCollisionError(
                f"IDENTITY LOCKED: '{identity}' is already registered to "
                f"container instance {existing.instance_id[:8]}. "
                f"This container instance ({instance_id[:8]}) cannot claim "
                f"the same identity. This indicates a duplicate container. "
                f"Do not attempt to troubleshoot -- stop one of the "
                f"duplicate containers."
            )
        else:
            # Expired lock -- clean up and allow registration
            logger.info(
                f"Expired identity lock for '{identity}' "
                f"(instance {existing.instance_id[:8]})"
            )

    _identity_registry[identity] = IdentityLock(
        instance_id=instance_id,
        last_seen=time.monotonic(),
        identity=identity,
    )
    logger.info(f"Identity '{identity}' registered (instance {instance_id[:8]})")


def _check_identity_available(identity: str) -> IdentityLock | None:
    """Check if an identity is locked by an enforced-mode caller.

    Returns the lock if active, None if available.

    Requirements: REQ-MCP-016
    """
    lock = _identity_registry.get(identity)
    if lock is None:
        return None

    if time.monotonic() - lock.last_seen > IDENTITY_LOCK_TTL_SECONDS:
        # Expired -- clean up
        del _identity_registry[identity]
        logger.info(f"Expired identity lock for '{identity}' cleaned up")
        return None

    return lock


def resolve_identity(ctx: Context, user_param: str = "claude") -> str:
    """
    Resolve the effective QMS identity from request context.

    Header-based mode selection (REQ-MCP-015):
    - X-QMS-Identity header present → Enforced mode (use header value)
    - X-QMS-Identity header absent → Trusted mode (use user parameter)

    Identity collision prevention (REQ-MCP-016):
    - Enforced-mode callers register their identity in the in-memory registry.
    - Trusted-mode callers are rejected if the identity is locked by an enforced-mode caller.
    - Duplicate enforced-mode callers (different instance_id) are rejected.

    Args:
        ctx: FastMCP Context (injected by framework)
        user_param: The user parameter from the tool call (used in trusted mode)

    Returns:
        The resolved QMS user identity string.

    Raises:
        IdentityCollisionError: If the identity is locked by another instance.

    Requirements: REQ-MCP-015, REQ-MCP-016
    """
    _cleanup_expired_locks()

    try:
        request_ctx = ctx.request_context
        if request_ctx is not None:
            request = request_ctx.request
            if request is not None and isinstance(request, Request):
                # HTTP request -- determine mode from header presence
                identity = request.headers.get("x-qms-identity")
                if identity:
                    # Enforced mode: header present
                    if identity not in KNOWN_AGENTS:
                        logger.warning(f"Unknown agent identity in header: {identity}")
                    if user_param != "claude" and user_param != identity:
                        logger.warning(
                            f"Identity mismatch: header={identity}, param={user_param}. "
                            f"Using enforced identity: {identity}"
                        )

                    # Register enforced identity (REQ-MCP-016)
                    instance_id = request.headers.get("x-qms-instance", "")
                    _register_identity(identity, instance_id)

                    return identity
                else:
                    # Trusted mode: header absent (REQ-MCP-015)
                    # Check for identity collision before allowing (REQ-MCP-016)
                    lock = _check_identity_available(user_param)
                    if lock is not None:
                        raise IdentityCollisionError(
                            f"IDENTITY LOCKED: '{user_param}' is active in enforced mode "
                            f"(container instance {lock.instance_id[:8]}). "
                            f"Trusted-mode request rejected. This identity is exclusively "
                            f"held by a running container. "
                            f"Do not attempt to troubleshoot -- the container is the "
                            f"authoritative holder of this identity."
                        )
                    return user_param
    except IdentityCollisionError:
        raise  # Propagate collision errors (REQ-MCP-016)
    except (AttributeError, LookupError):
        pass  # No request context available -- defensive fallback

    # Defensive fallback: no request context available
    # (e.g., testing, future transport changes)
    # Check for identity collision before allowing (REQ-MCP-016)
    lock = _check_identity_available(user_param)
    if lock is not None:
        raise IdentityCollisionError(
            f"IDENTITY LOCKED: '{user_param}' is active in enforced mode "
            f"(container instance {lock.instance_id[:8]}). "
            f"Request rejected. This identity is exclusively held by "
            f"a running container. "
            f"Do not attempt to troubleshoot -- the container is the "
            f"authoritative holder of this identity."
        )

    return user_param


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """
    Parse command-line arguments for the MCP server.

    Args:
        args: Command-line arguments (defaults to sys.argv[1:] if None)

    Returns:
        Parsed arguments namespace

    Requirements: REQ-MCP-012
    """
    parser = argparse.ArgumentParser(
        description="QMS MCP Server - Model Context Protocol server for QMS operations"
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="Transport: stdio (default), sse (deprecated), or streamable-http (recommended for remote)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host address to bind for remote transports (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind for remote transports (default: 8000)",
    )
    parser.add_argument(
        "--project-root",
        dest="project_root",
        help="Project root directory (default: auto-discover from QMS/ or qms.config.json)",
    )
    return parser.parse_args(args)


def get_qms_root() -> Path | None:
    """
    Determine the QMS root directory.

    Resolution order (per REQ-MCP-013):
    1. --project-root CLI argument (stored in QMS_PROJECT_ROOT env var by main())
    2. QMS_PROJECT_ROOT environment variable
    3. Auto-discovery by walking up from cwd looking for QMS/ directory

    Returns None if not found.

    Requirements: REQ-MCP-013
    """
    # Check environment variable first (set by CLI arg or directly)
    env_root = os.environ.get("QMS_PROJECT_ROOT")
    if env_root:
        path = Path(env_root)
        if (path / "QMS").is_dir():
            logger.info(f"Using project root from QMS_PROJECT_ROOT: {path}")
            return path
        else:
            logger.warning(
                f"QMS_PROJECT_ROOT={env_root} does not contain QMS/ directory"
            )

    # Fall back to directory walking
    cwd = Path.cwd()

    # Check current directory and parents for QMS/
    for parent in [cwd] + list(cwd.parents):
        qms_path = parent / "QMS"
        if qms_path.is_dir():
            return parent

    return None


def run_qms_command(args: list[str], user: str = "claude") -> dict:
    """
    Execute a QMS CLI command and return the result.

    Args:
        args: Command arguments (e.g., ["inbox"], ["status", "CR-001"])
        user: The QMS user identity (default: "claude")

    Returns:
        dict with keys:
            - success: bool
            - output: str (command output or error message)
            - return_code: int
    """
    qms_root = get_qms_root()
    if qms_root is None:
        return {
            "success": False,
            "output": "Error: Could not find QMS root directory. Ensure you are in a QMS project.",
            "return_code": 1,
        }

    # Build the command
    # The qms.py script is in qms-cli/ relative to the project root
    qms_script = qms_root / "qms-cli" / "qms.py"
    if not qms_script.exists():
        return {
            "success": False,
            "output": f"Error: QMS CLI not found at {qms_script}",
            "return_code": 1,
        }

    cmd = [sys.executable, str(qms_script), "--user", user] + args

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(qms_root),
            timeout=30,
            stdin=subprocess.DEVNULL,
        )

        output = result.stdout
        if result.stderr:
            output += "\n" + result.stderr if output else result.stderr

        return {
            "success": result.returncode == 0,
            "output": output.strip() if output else "(no output)",
            "return_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "Error: Command timed out after 30 seconds",
            "return_code": -1,
        }
    except Exception as e:
        return {
            "success": False,
            "output": f"Error executing command: {e}",
            "return_code": -1,
        }


def main(cli_args: list[str] | None = None):
    """
    Entry point for the QMS MCP server.

    Args:
        cli_args: Command-line arguments (defaults to sys.argv[1:] if None)

    Requirements: REQ-MCP-011, REQ-MCP-012, REQ-MCP-013, REQ-MCP-014
    """
    args = parse_args(cli_args)

    # Set project root in environment if specified via CLI
    # CLI argument takes precedence over existing env var (per REQ-MCP-013)
    if args.project_root:
        os.environ["QMS_PROJECT_ROOT"] = args.project_root
        logger.info(f"Project root set from --project-root: {args.project_root}")

    logger.info(f"Starting QMS MCP Server (transport={args.transport})")

    # Import and register tools (deferred to avoid circular imports)
    from .tools import register_tools

    register_tools(mcp, run_qms_command, resolve_identity)

    # Run with selected transport (per REQ-MCP-011, REQ-MCP-014)
    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport == "streamable-http":
        # Streamable-HTTP transport for remote connections (recommended per REQ-MCP-014)
        # Configure host/port via settings (FastMCP.run() doesn't accept these as kwargs)
        mcp.settings.host = args.host
        mcp.settings.port = args.port

        # Allow container connections via host.docker.internal
        mcp.settings.transport_security.allowed_hosts.append("host.docker.internal:*")
        mcp.settings.transport_security.allowed_origins.append(
            "http://host.docker.internal:*"
        )

        # Stateless mode: disables server-side session tracking.
        # Prevents stale Mcp-Session-Id reuse across container restarts (see #9608).
        mcp.settings.stateless_http = True

        logger.info(f"Binding to {args.host}:{args.port} (streamable-http, stateless)")
        mcp.run(transport="streamable-http")
    else:
        # SSE transport for remote connections (deprecated, retained for backward compatibility)
        # Configure host/port via settings (FastMCP.run() doesn't accept these as kwargs)
        mcp.settings.host = args.host
        mcp.settings.port = args.port

        # Allow container connections via host.docker.internal
        mcp.settings.transport_security.allowed_hosts.append("host.docker.internal:*")
        mcp.settings.transport_security.allowed_origins.append(
            "http://host.docker.internal:*"
        )

        logger.info(f"Binding to {args.host}:{args.port} (sse - deprecated)")
        mcp.run(transport="sse")


if __name__ == "__main__":
    main()
