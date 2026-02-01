"""
QMS MCP Tools

Tool definitions for QMS operations exposed via MCP.

Requirements: REQ-MCP-002 through REQ-MCP-006
"""

from typing import Callable


def register_tools(mcp, run_qms_command: Callable):
    """
    Register all QMS tools with the MCP server.

    Args:
        mcp: The FastMCP server instance
        run_qms_command: Function to execute QMS CLI commands
    """

    # =========================================================================
    # REQ-MCP-002: User Command Tools
    # =========================================================================

    @mcp.tool()
    def qms_inbox(user: str = "claude") -> str:
        """
        Check the QMS inbox for pending tasks assigned to a user.

        Shows documents awaiting review, approval, or other action.

        Args:
            user: QMS user identity (default: "claude")

        Returns:
            List of pending inbox items or message if inbox is empty.

        Requirement: REQ-MCP-002
        """
        result = run_qms_command(["inbox"], user=user)
        return result["output"]

    @mcp.tool()
    def qms_workspace(user: str = "claude") -> str:
        """
        List documents currently checked out to a user's workspace.

        Shows all documents the user has locked for editing.

        Args:
            user: QMS user identity (default: "claude")

        Returns:
            List of checked-out documents or message if workspace is empty.

        Requirement: REQ-MCP-002
        """
        result = run_qms_command(["workspace"], user=user)
        return result["output"]

    @mcp.tool()
    def qms_status(doc_id: str) -> str:
        """
        Get the current status of a QMS document.

        Displays document state, version, owner, and workflow status.

        Args:
            doc_id: Document identifier (e.g., "CR-001", "SOP-001")

        Returns:
            Document status information or error if not found.

        Requirement: REQ-MCP-002
        """
        result = run_qms_command(["status", doc_id])
        return result["output"]

    @mcp.tool()
    def qms_read(
        doc_id: str,
        version: str = "",
        draft: bool = False,
    ) -> str:
        """
        Read the content of a QMS document.

        Retrieves document content with options for specific versions.

        Args:
            doc_id: Document identifier (e.g., "CR-001", "SOP-001")
            version: Specific version to read (e.g., "1.0", "2.1"). Empty for current.
            draft: If True, read the current draft version instead of effective.

        Returns:
            Document content or error if not found.

        Requirement: REQ-MCP-002
        """
        args = ["read", doc_id]
        if version:
            args.extend(["--version", version])
        if draft:
            args.append("--draft")
        result = run_qms_command(args)
        return result["output"]

    @mcp.tool()
    def qms_history(doc_id: str) -> str:
        """
        View the audit trail for a QMS document.

        Shows all recorded events in chronological order.

        Args:
            doc_id: Document identifier (e.g., "CR-001", "SOP-001")

        Returns:
            Audit trail events or error if not found.

        Requirement: REQ-MCP-002
        """
        result = run_qms_command(["history", doc_id])
        return result["output"]

    @mcp.tool()
    def qms_comments(doc_id: str, version: str = "") -> str:
        """
        View review comments for a QMS document.

        Extracts comments from REVIEW and REJECT events in the audit trail.

        Args:
            doc_id: Document identifier (e.g., "CR-001", "SOP-001")
            version: Filter comments by version (optional).

        Returns:
            Review comments or message if none found.

        Requirement: REQ-MCP-002
        """
        args = ["comments", doc_id]
        if version:
            args.extend(["--version", version])
        result = run_qms_command(args)
        return result["output"]

    # =========================================================================
    # REQ-MCP-003: Document Lifecycle Tools
    # =========================================================================

    @mcp.tool()
    def qms_create(
        doc_type: str,
        title: str,
        parent: str = "",
        name: str = "",
        user: str = "claude",
    ) -> str:
        """
        Create a new QMS document.

        Creates a draft document of the specified type.

        Args:
            doc_type: Document type (e.g., "CR", "SOP", "INV", "VAR", "TP")
            title: Document title
            parent: Parent document ID for child types (VAR, TP, ER)
            name: Name for TEMPLATE documents (required for TEMPLATE type)
            user: QMS user identity (default: "claude")

        Returns:
            Confirmation with new document ID or error message.

        Requirement: REQ-MCP-003
        """
        args = ["create", doc_type, "--title", title]
        if parent:
            args.extend(["--parent", parent])
        if name:
            args.extend(["--name", name])
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

        Requirement: REQ-MCP-003
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

        Requirement: REQ-MCP-003
        """
        result = run_qms_command(["checkin", doc_id], user=user)
        return result["output"]

    @mcp.tool()
    def qms_cancel(doc_id: str, confirm: bool = False, user: str = "claude") -> str:
        """
        Cancel a never-effective QMS document.

        Permanently deletes a document that has never been approved (version < 1.0).

        Args:
            doc_id: Document identifier (e.g., "CR-001")
            confirm: Must be True to confirm cancellation (safety check)
            user: QMS user identity (default: "claude")

        Returns:
            Confirmation of cancellation or error message.

        Requirement: REQ-MCP-003
        """
        if not confirm:
            return "Error: confirm must be True to cancel a document. This action is permanent."
        args = ["cancel", doc_id, "--confirm"]
        result = run_qms_command(args, user=user)
        return result["output"]

    # =========================================================================
    # REQ-MCP-004: Workflow Tools
    # =========================================================================

    @mcp.tool()
    def qms_route(
        doc_id: str,
        route_type: str,
        retire: bool = False,
        user: str = "claude",
    ) -> str:
        """
        Route a QMS document for review or approval.

        Transitions document to the next workflow stage.

        Args:
            doc_id: Document identifier (e.g., "CR-001")
            route_type: Routing action - "review" or "approval"
            retire: If True, route for retirement approval
            user: QMS user identity (default: "claude")

        Returns:
            Confirmation of routing or error message.

        Requirement: REQ-MCP-004
        """
        if route_type not in ("review", "approval"):
            return f"Error: route_type must be 'review' or 'approval', got '{route_type}'"

        args = ["route", doc_id, f"--{route_type}"]
        if retire:
            args.append("--retire")
        result = run_qms_command(args, user=user)
        return result["output"]

    @mcp.tool()
    def qms_assign(
        doc_id: str,
        assignees: list[str],
        user: str = "claude",
    ) -> str:
        """
        Add reviewers or approvers to a document.

        Assigns additional users to review or approve a document in workflow.

        Args:
            doc_id: Document identifier (e.g., "CR-001")
            assignees: List of user IDs to assign (e.g., ["tu_ui", "tu_scene"])
            user: QMS user identity - must be in quality group (default: "claude")

        Returns:
            Confirmation of assignment or error message.

        Requirement: REQ-MCP-004
        """
        args = ["assign", doc_id, "--assignees"] + assignees
        result = run_qms_command(args, user=user)
        return result["output"]

    @mcp.tool()
    def qms_review(
        doc_id: str,
        outcome: str,
        comment: str = "",
        user: str = "claude",
    ) -> str:
        """
        Submit a review for a QMS document.

        Records review decision with optional comment.

        Args:
            doc_id: Document identifier (e.g., "CR-001")
            outcome: Review outcome - "recommend" or "request-updates"
            comment: Review comments (optional but encouraged)
            user: QMS user identity (default: "claude")

        Returns:
            Confirmation of review or error message.

        Requirement: REQ-MCP-004
        """
        if outcome not in ("recommend", "request-updates"):
            return f"Error: outcome must be 'recommend' or 'request-updates', got '{outcome}'"

        args = ["review", doc_id, "--outcome", outcome]
        if comment:
            args.extend(["--comment", comment])
        result = run_qms_command(args, user=user)
        return result["output"]

    @mcp.tool()
    def qms_approve(doc_id: str, user: str = "claude") -> str:
        """
        Approve a QMS document.

        Completes approval workflow and increments document version.

        Args:
            doc_id: Document identifier (e.g., "CR-001")
            user: QMS user identity (default: "claude")

        Returns:
            Confirmation of approval with new version or error message.

        Requirement: REQ-MCP-004
        """
        result = run_qms_command(["approve", doc_id], user=user)
        return result["output"]

    @mcp.tool()
    def qms_reject(
        doc_id: str,
        comment: str,
        user: str = "claude",
    ) -> str:
        """
        Reject a QMS document.

        Returns document to reviewed state for revision.

        Args:
            doc_id: Document identifier (e.g., "CR-001")
            comment: Rejection rationale (required)
            user: QMS user identity (default: "claude")

        Returns:
            Confirmation of rejection or error message.

        Requirement: REQ-MCP-004
        """
        if not comment:
            return "Error: comment is required when rejecting a document."
        args = ["reject", doc_id, "--comment", comment]
        result = run_qms_command(args, user=user)
        return result["output"]

    # =========================================================================
    # REQ-MCP-005: Execution Tools
    # =========================================================================

    @mcp.tool()
    def qms_release(doc_id: str, user: str = "claude") -> str:
        """
        Release an executable document for execution.

        Transitions document from PRE_APPROVED to IN_EXECUTION.

        Args:
            doc_id: Document identifier for an executable document (e.g., "CR-001")
            user: QMS user identity - must be document owner (default: "claude")

        Returns:
            Confirmation of release or error message.

        Requirement: REQ-MCP-005
        """
        result = run_qms_command(["release", doc_id], user=user)
        return result["output"]

    @mcp.tool()
    def qms_revert(
        doc_id: str,
        reason: str,
        user: str = "claude",
    ) -> str:
        """
        Revert an executable document to execution.

        Transitions document from POST_REVIEWED back to IN_EXECUTION.

        Args:
            doc_id: Document identifier for an executable document (e.g., "CR-001")
            reason: Explanation for why revert is needed (required)
            user: QMS user identity - must be document owner (default: "claude")

        Returns:
            Confirmation of revert or error message.

        Requirement: REQ-MCP-005
        """
        if not reason:
            return "Error: reason is required when reverting a document."
        args = ["revert", doc_id, "--reason", reason]
        result = run_qms_command(args, user=user)
        return result["output"]

    @mcp.tool()
    def qms_close(doc_id: str, user: str = "claude") -> str:
        """
        Close an executable document.

        Transitions document from POST_APPROVED to CLOSED (terminal state).

        Args:
            doc_id: Document identifier for an executable document (e.g., "CR-001")
            user: QMS user identity - must be document owner (default: "claude")

        Returns:
            Confirmation of closure or error message.

        Requirement: REQ-MCP-005
        """
        result = run_qms_command(["close", doc_id], user=user)
        return result["output"]

    # =========================================================================
    # REQ-MCP-006: Administrative Tools
    # =========================================================================

    @mcp.tool()
    def qms_fix(doc_id: str, user: str = "claude") -> str:
        """
        Perform an administrative fix on an EFFECTIVE document.

        Allows minor corrections to effective documents without full revision cycle.
        Requires administrator privileges.

        Args:
            doc_id: Document identifier (e.g., "SOP-001")
            user: QMS user identity - must be administrator (default: "claude")

        Returns:
            Confirmation of fix or error message.

        Requirement: REQ-MCP-006
        """
        result = run_qms_command(["fix", doc_id], user=user)
        return result["output"]
