"""
QMS MCP Tools

Tool definitions for QMS operations exposed via MCP.

Requirements: REQ-MCP-002 through REQ-MCP-006, REQ-MCP-015
"""

from typing import Callable

from mcp.server.fastmcp import Context


def register_tools(mcp, run_qms_command: Callable, resolve_identity: Callable):
    """
    Register all QMS tools with the MCP server.

    Args:
        mcp: The FastMCP server instance
        run_qms_command: Function to execute QMS CLI commands
        resolve_identity: Function to resolve caller identity from transport context
    """

    # =========================================================================
    # REQ-MCP-002: User Command Tools
    # =========================================================================

    @mcp.tool()
    def qms_inbox(ctx: Context, user: str) -> str:
        """
        Check the QMS inbox for pending tasks assigned to a user.

        Shows documents awaiting review, approval, or other action.

        Args:
            user: QMS user identity

        Returns:
            List of pending inbox items or message if inbox is empty.

        Requirement: REQ-MCP-002
        """
        resolved = resolve_identity(ctx, user)
        result = run_qms_command(["inbox"], user=resolved)
        return result["output"]

    @mcp.tool()
    def qms_workspace(ctx: Context, user: str) -> str:
        """
        List documents currently checked out to a user's workspace.

        Shows all documents the user has locked for editing.

        Args:
            user: QMS user identity

        Returns:
            List of checked-out documents or message if workspace is empty.

        Requirement: REQ-MCP-002
        """
        resolved = resolve_identity(ctx, user)
        result = run_qms_command(["workspace"], user=resolved)
        return result["output"]

    @mcp.tool()
    def qms_status(ctx: Context, doc_id: str, user: str) -> str:
        """
        Get the current status of a QMS document.

        Displays document state, version, owner, and workflow status.

        Args:
            doc_id: Document identifier (e.g., "CR-001", "SOP-001")
            user: QMS user identity

        Returns:
            Document status information or error if not found.

        Requirement: REQ-MCP-002
        """
        resolved = resolve_identity(ctx, user)
        result = run_qms_command(["status", doc_id], user=resolved)
        return result["output"]

    @mcp.tool()
    def qms_read(
        ctx: Context,
        doc_id: str,
        user: str,
        version: str = "",
        draft: bool = False,
    ) -> str:
        """
        Read the content of a QMS document.

        Retrieves document content with options for specific versions.

        Args:
            doc_id: Document identifier (e.g., "CR-001", "SOP-001")
            user: QMS user identity
            version: Specific version to read (e.g., "1.0", "2.1"). Empty for current.
            draft: If True, read the current draft version instead of effective.

        Returns:
            Document content or error if not found.

        Requirement: REQ-MCP-002
        """
        resolved = resolve_identity(ctx, user)
        args = ["read", doc_id]
        if version:
            args.extend(["--version", version])
        if draft:
            args.append("--draft")
        result = run_qms_command(args, user=resolved)
        return result["output"]

    @mcp.tool()
    def qms_history(ctx: Context, doc_id: str, user: str) -> str:
        """
        View the audit trail for a QMS document.

        Shows all recorded events in chronological order.

        Args:
            doc_id: Document identifier (e.g., "CR-001", "SOP-001")
            user: QMS user identity

        Returns:
            Audit trail events or error if not found.

        Requirement: REQ-MCP-002
        """
        resolved = resolve_identity(ctx, user)
        result = run_qms_command(["history", doc_id], user=resolved)
        return result["output"]

    @mcp.tool()
    def qms_comments(ctx: Context, doc_id: str, user: str, version: str = "") -> str:
        """
        View review comments for a QMS document.

        Extracts comments from REVIEW and REJECT events in the audit trail.

        Args:
            doc_id: Document identifier (e.g., "CR-001", "SOP-001")
            user: QMS user identity
            version: Filter comments by version (optional).

        Returns:
            Review comments or message if none found.

        Requirement: REQ-MCP-002
        """
        resolved = resolve_identity(ctx, user)
        args = ["comments", doc_id]
        if version:
            args.extend(["--version", version])
        result = run_qms_command(args, user=resolved)
        return result["output"]

    # =========================================================================
    # REQ-MCP-003: Document Lifecycle Tools
    # =========================================================================

    @mcp.tool()
    def qms_create(
        ctx: Context,
        doc_type: str,
        title: str,
        user: str,
        parent: str = "",
        name: str = "",
    ) -> str:
        """
        Create a new QMS document.

        Creates a draft document of the specified type.

        Args:
            doc_type: Document type (e.g., "CR", "SOP", "INV", "VAR", "TP")
            title: Document title
            user: QMS user identity
            parent: Parent document ID for child types (VAR, TP, ER)
            name: Name for TEMPLATE documents (required for TEMPLATE type)

        Returns:
            Confirmation with new document ID or error message.

        Requirement: REQ-MCP-003
        """
        resolved = resolve_identity(ctx, user)
        args = ["create", doc_type, "--title", title]
        if parent:
            args.extend(["--parent", parent])
        if name:
            args.extend(["--name", name])
        result = run_qms_command(args, user=resolved)
        return result["output"]

    @mcp.tool()
    def qms_checkout(ctx: Context, doc_id: str, user: str) -> str:
        """
        Check out a QMS document for editing.

        Locks the document and copies it to the user's workspace.

        Args:
            doc_id: Document identifier (e.g., "CR-001")
            user: QMS user identity

        Returns:
            Path to workspace copy or error message.

        Requirement: REQ-MCP-003
        """
        resolved = resolve_identity(ctx, user)
        result = run_qms_command(["checkout", doc_id], user=resolved)
        return result["output"]

    @mcp.tool()
    def qms_checkin(ctx: Context, doc_id: str, user: str) -> str:
        """
        Check in a QMS document after editing.

        Unlocks the document and applies workspace changes.

        Args:
            doc_id: Document identifier (e.g., "CR-001")
            user: QMS user identity

        Returns:
            Confirmation with new version or error message.

        Requirement: REQ-MCP-003
        """
        resolved = resolve_identity(ctx, user)
        result = run_qms_command(["checkin", doc_id], user=resolved)
        return result["output"]

    @mcp.tool()
    def qms_cancel(ctx: Context, doc_id: str, user: str, confirm: bool = False) -> str:
        """
        Cancel a never-effective QMS document.

        Permanently deletes a document that has never been approved (version < 1.0).

        Args:
            doc_id: Document identifier (e.g., "CR-001")
            user: QMS user identity
            confirm: Must be True to confirm cancellation (safety check)

        Returns:
            Confirmation of cancellation or error message.

        Requirement: REQ-MCP-003
        """
        if not confirm:
            return "Error: confirm must be True to cancel a document. This action is permanent."
        resolved = resolve_identity(ctx, user)
        args = ["cancel", doc_id, "--confirm"]
        result = run_qms_command(args, user=resolved)
        return result["output"]

    # =========================================================================
    # REQ-MCP-004: Workflow Tools
    # =========================================================================

    @mcp.tool()
    def qms_route(
        ctx: Context,
        doc_id: str,
        route_type: str,
        user: str,
        retire: bool = False,
    ) -> str:
        """
        Route a QMS document for review or approval.

        Transitions document to the next workflow stage.

        Args:
            doc_id: Document identifier (e.g., "CR-001")
            route_type: Routing action - "review" or "approval"
            user: QMS user identity
            retire: If True, route for retirement approval

        Returns:
            Confirmation of routing or error message.

        Requirement: REQ-MCP-004
        """
        if route_type not in ("review", "approval"):
            return f"Error: route_type must be 'review' or 'approval', got '{route_type}'"

        resolved = resolve_identity(ctx, user)
        args = ["route", doc_id, f"--{route_type}"]
        if retire:
            args.append("--retire")
        result = run_qms_command(args, user=resolved)
        return result["output"]

    @mcp.tool()
    def qms_assign(
        ctx: Context,
        doc_id: str,
        assignees: list[str],
        user: str,
    ) -> str:
        """
        Add reviewers or approvers to a document.

        Assigns additional users to review or approve a document in workflow.

        Args:
            doc_id: Document identifier (e.g., "CR-001")
            assignees: List of user IDs to assign (e.g., ["tu_ui", "tu_scene"])
            user: QMS user identity - must be in quality group

        Returns:
            Confirmation of assignment or error message.

        Requirement: REQ-MCP-004
        """
        resolved = resolve_identity(ctx, user)
        args = ["assign", doc_id, "--assignees"] + assignees
        result = run_qms_command(args, user=resolved)
        return result["output"]

    @mcp.tool()
    def qms_review(
        ctx: Context,
        doc_id: str,
        outcome: str,
        user: str,
        comment: str = "",
    ) -> str:
        """
        Submit a review for a QMS document.

        Records review decision with optional comment.

        Args:
            doc_id: Document identifier (e.g., "CR-001")
            outcome: Review outcome - "recommend" or "request-updates"
            user: QMS user identity
            comment: Review comments (optional but encouraged)

        Returns:
            Confirmation of review or error message.

        Requirement: REQ-MCP-004
        """
        if outcome not in ("recommend", "request-updates"):
            return f"Error: outcome must be 'recommend' or 'request-updates', got '{outcome}'"

        resolved = resolve_identity(ctx, user)
        args = ["review", doc_id, f"--{outcome}"]
        if comment:
            args.extend(["--comment", comment])
        result = run_qms_command(args, user=resolved)
        return result["output"]

    @mcp.tool()
    def qms_approve(ctx: Context, doc_id: str, user: str) -> str:
        """
        Approve a QMS document.

        Completes approval workflow and increments document version.

        Args:
            doc_id: Document identifier (e.g., "CR-001")
            user: QMS user identity

        Returns:
            Confirmation of approval with new version or error message.

        Requirement: REQ-MCP-004
        """
        resolved = resolve_identity(ctx, user)
        result = run_qms_command(["approve", doc_id], user=resolved)
        return result["output"]

    @mcp.tool()
    def qms_reject(
        ctx: Context,
        doc_id: str,
        comment: str,
        user: str,
    ) -> str:
        """
        Reject a QMS document.

        Returns document to reviewed state for revision.

        Args:
            doc_id: Document identifier (e.g., "CR-001")
            comment: Rejection rationale (required)
            user: QMS user identity

        Returns:
            Confirmation of rejection or error message.

        Requirement: REQ-MCP-004
        """
        if not comment:
            return "Error: comment is required when rejecting a document."
        resolved = resolve_identity(ctx, user)
        args = ["reject", doc_id, "--comment", comment]
        result = run_qms_command(args, user=resolved)
        return result["output"]

    @mcp.tool()
    def qms_withdraw(ctx: Context, doc_id: str, user: str) -> str:
        """
        Withdraw a document from review or approval workflow.

        Returns document to its previous state before routing.

        Args:
            doc_id: Document identifier (e.g., "CR-001")
            user: QMS user identity - must be document owner

        Returns:
            Confirmation of withdrawal or error message.

        Requirement: REQ-MCP-004
        """
        resolved = resolve_identity(ctx, user)
        result = run_qms_command(["withdraw", doc_id], user=resolved)
        return result["output"]

    # =========================================================================
    # REQ-MCP-005: Execution Tools
    # =========================================================================

    @mcp.tool()
    def qms_release(ctx: Context, doc_id: str, user: str) -> str:
        """
        Release an executable document for execution.

        Transitions document from PRE_APPROVED to IN_EXECUTION.

        Args:
            doc_id: Document identifier for an executable document (e.g., "CR-001")
            user: QMS user identity - must be document owner

        Returns:
            Confirmation of release or error message.

        Requirement: REQ-MCP-005
        """
        resolved = resolve_identity(ctx, user)
        result = run_qms_command(["release", doc_id], user=resolved)
        return result["output"]

    @mcp.tool()
    def qms_revert(
        ctx: Context,
        doc_id: str,
        reason: str,
        user: str,
    ) -> str:
        """
        Revert an executable document to execution.

        Transitions document from POST_REVIEWED back to IN_EXECUTION.

        Args:
            doc_id: Document identifier for an executable document (e.g., "CR-001")
            reason: Explanation for why revert is needed (required)
            user: QMS user identity - must be document owner

        Returns:
            Confirmation of revert or error message.

        Requirement: REQ-MCP-005
        """
        if not reason:
            return "Error: reason is required when reverting a document."
        resolved = resolve_identity(ctx, user)
        args = ["revert", doc_id, "--reason", reason]
        result = run_qms_command(args, user=resolved)
        return result["output"]

    @mcp.tool()
    def qms_close(ctx: Context, doc_id: str, user: str) -> str:
        """
        Close an executable document.

        Transitions document from POST_APPROVED to CLOSED (terminal state).

        Args:
            doc_id: Document identifier for an executable document (e.g., "CR-001")
            user: QMS user identity - must be document owner

        Returns:
            Confirmation of closure or error message.

        Requirement: REQ-MCP-005
        """
        resolved = resolve_identity(ctx, user)
        result = run_qms_command(["close", doc_id], user=resolved)
        return result["output"]

    # =========================================================================
    # REQ-INT-022 / REQ-MCP-007: Interactive Authoring Tool
    # =========================================================================

    @mcp.tool()
    def qms_interact(
        ctx: Context,
        doc_id: str,
        user: str,
        respond: str = "",
        file: str = "",
        reason: str = "",
        goto: str = "",
        cancel_goto: bool = False,
        reopen: str = "",
        progress: bool = False,
        compile: bool = False,
    ) -> str:
        """
        Interactive document authoring via template-driven prompting.

        Presents prompts from an interactive template, records responses,
        and manages the authoring session. Bare invocation (no flags)
        shows status and current prompt.

        Args:
            doc_id: Document identifier (e.g., "CR-091-VR-001")
            user: QMS user identity
            respond: Response value for the current prompt
            file: Path to file containing response value
            reason: Reason for amendment or loop reopen
            goto: Navigate to a prompt for amendment
            cancel_goto: Cancel active goto and return
            reopen: Reopen a closed loop
            progress: Show all prompts with fill status
            compile: Preview compiled markdown output

        Returns:
            Current prompt info, response confirmation, or compiled output.

        Requirement: REQ-INT-022
        """
        resolved = resolve_identity(ctx, user)
        args = ["interact", doc_id]

        if progress:
            args.append("--progress")
        elif compile:
            args.append("--compile")
        elif cancel_goto:
            args.append("--cancel-goto")
        elif goto:
            args.extend(["--goto", goto])
            if reason:
                args.extend(["--reason", reason])
        elif reopen:
            args.extend(["--reopen", reopen])
            if reason:
                args.extend(["--reason", reason])
        elif respond or file:
            if file:
                args.extend(["--respond", "--file", file])
            else:
                args.extend(["--respond", respond])
            if reason:
                args.extend(["--reason", reason])

        result = run_qms_command(args, user=resolved)
        return result["output"]

    # =========================================================================
    # REQ-MCP-006: Administrative Tools
    # =========================================================================

    @mcp.tool()
    def qms_fix(ctx: Context, doc_id: str, user: str) -> str:
        """
        Perform an administrative fix on an EFFECTIVE document.

        Allows minor corrections to effective documents without full revision cycle.
        Requires administrator privileges.

        Args:
            doc_id: Document identifier (e.g., "SOP-001")
            user: QMS user identity - must be administrator

        Returns:
            Confirmation of fix or error message.

        Requirement: REQ-MCP-006
        """
        resolved = resolve_identity(ctx, user)
        result = run_qms_command(["fix", doc_id], user=resolved)
        return result["output"]
