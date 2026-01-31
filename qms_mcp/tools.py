"""
QMS MCP Tools

Tool definitions for QMS operations exposed via MCP.

Requirements: REQ-MCP-003 through REQ-MCP-010
"""

from typing import Callable


def register_tools(mcp, run_qms_command: Callable):
    """
    Register all QMS tools with the MCP server.

    Args:
        mcp: The FastMCP server instance
        run_qms_command: Function to execute QMS CLI commands
    """

    @mcp.tool()
    def qms_inbox(user: str = "claude") -> str:
        """
        Check the QMS inbox for pending tasks assigned to a user.

        Shows documents awaiting review, approval, or other action.

        Args:
            user: QMS user identity (default: "claude")

        Returns:
            List of pending inbox items or message if inbox is empty.

        Requirement: REQ-MCP-003
        """
        result = run_qms_command(["inbox"], user=user)
        return result["output"]

    @mcp.tool()
    def qms_status(doc_id: str) -> str:
        """
        Get the current status of a QMS document.

        Displays document state, version, owner, and workflow history.

        Args:
            doc_id: Document identifier (e.g., "CR-001", "SOP-001")

        Returns:
            Document status information or error if not found.

        Requirement: REQ-MCP-004
        """
        result = run_qms_command(["status", doc_id])
        return result["output"]

    @mcp.tool()
    def qms_create(doc_type: str, title: str, user: str = "claude") -> str:
        """
        Create a new QMS document.

        Creates a draft document of the specified type.

        Args:
            doc_type: Document type (e.g., "CR", "SOP", "INV", "CAPA")
            title: Document title
            user: QMS user identity (default: "claude")

        Returns:
            Confirmation with new document ID or error message.

        Requirement: REQ-MCP-005
        """
        result = run_qms_command(["create", doc_type, "--title", title], user=user)
        return result["output"]

    @mcp.tool()
    def qms_route(
        doc_id: str,
        route_type: str,
        user: str = "claude",
    ) -> str:
        """
        Route a QMS document for review or approval.

        Transitions document to the next workflow stage.

        Args:
            doc_id: Document identifier (e.g., "CR-001")
            route_type: Routing action - "review" or "approval"
            user: QMS user identity (default: "claude")

        Returns:
            Confirmation of routing or error message.

        Requirement: REQ-MCP-006
        """
        if route_type not in ("review", "approval"):
            return f"Error: route_type must be 'review' or 'approval', got '{route_type}'"

        result = run_qms_command(["route", doc_id, f"--{route_type}"], user=user)
        return result["output"]

    @mcp.tool()
    def qms_approve(
        doc_id: str,
        action: str,
        comments: str = "",
        user: str = "claude",
    ) -> str:
        """
        Approve or reject a QMS document.

        Applies approval decision to a document in review.

        Args:
            doc_id: Document identifier (e.g., "CR-001")
            action: Approval action - "approve" or "reject"
            comments: Optional comments for the approval/rejection
            user: QMS user identity (default: "claude")

        Returns:
            Confirmation of action or error message.

        Requirement: REQ-MCP-007
        """
        if action not in ("approve", "reject"):
            return f"Error: action must be 'approve' or 'reject', got '{action}'"

        args = [action, doc_id]
        if comments:
            args.extend(["--comments", comments])

        result = run_qms_command(args, user=user)
        return result["output"]

    @mcp.tool()
    def qms_checkout(doc_id: str, user: str = "claude") -> str:
        """
        Check out a QMS document for editing.

        Locks the document and copies it to the user's workspace.

        Args:
            doc_id: Document identifier (e.g., "CR-001")
            user: QMS user identity (default: "claude")

        Returns:
            Path to workspace copy or error message.

        Requirement: REQ-MCP-008
        """
        result = run_qms_command(["checkout", doc_id], user=user)
        return result["output"]

    @mcp.tool()
    def qms_checkin(doc_id: str, user: str = "claude") -> str:
        """
        Check in a QMS document after editing.

        Unlocks the document and applies workspace changes.

        Args:
            doc_id: Document identifier (e.g., "CR-001")
            user: QMS user identity (default: "claude")

        Returns:
            Confirmation with new version or error message.

        Requirement: REQ-MCP-009
        """
        result = run_qms_command(["checkin", doc_id], user=user)
        return result["output"]
