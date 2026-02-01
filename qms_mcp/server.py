"""
QMS MCP Server

Model Context Protocol server for the Quality Management System CLI.
Exposes QMS operations as MCP tools for integration with Claude Code and other MCP clients.

Requirements: REQ-MCP-001, REQ-MCP-002
"""

import logging
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


def get_qms_root() -> Path | None:
    """
    Determine the QMS root directory.

    Looks for QMS/ directory by walking up from the current working directory.
    Returns None if not found.
    """
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


def main():
    """Entry point for the QMS MCP server."""
    logger.info("Starting QMS MCP Server")

    # Import and register tools (deferred to avoid circular imports)
    from .tools import register_tools
    register_tools(mcp, run_qms_command)

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
