"""
QMS MCP Server

Model Context Protocol server for the Quality Management System CLI.
Exposes QMS operations as MCP tools for integration with Claude Code and other MCP clients.

Requirements: REQ-MCP-001, REQ-MCP-002, REQ-MCP-011, REQ-MCP-012, REQ-MCP-013, REQ-MCP-014
"""

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Configure logging to stderr (CRITICAL: never write to stdout for stdio transport)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("qms-mcp")

# Initialize FastMCP server
mcp = FastMCP("qms")


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

    register_tools(mcp, run_qms_command)

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

        logger.info(f"Binding to {args.host}:{args.port} (streamable-http)")
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
