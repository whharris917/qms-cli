"""
QMS Workflow Engine

Data-driven state machine for document workflow transitions.
Centralizes all transition logic that was previously scattered across commands.

Created as part of CR-026: QMS CLI Extensibility Refactoring
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Set, Tuple

from qms_config import Status, TRANSITIONS


class WorkflowType(Enum):
    """Types of workflow phases."""
    # Non-executable workflows
    REVIEW = "REVIEW"
    APPROVAL = "APPROVAL"

    # Executable workflows
    PRE_REVIEW = "PRE_REVIEW"
    PRE_APPROVAL = "PRE_APPROVAL"
    POST_REVIEW = "POST_REVIEW"
    POST_APPROVAL = "POST_APPROVAL"


class ExecutionPhase(Enum):
    """Execution phase for executable documents."""
    PRE_RELEASE = "pre_release"
    POST_RELEASE = "post_release"


class Action(Enum):
    """Actions that can be performed on documents."""
    ROUTE_REVIEW = "route_review"
    ROUTE_APPROVAL = "route_approval"
    REVIEW = "review"
    APPROVE = "approve"
    REJECT = "reject"
    RELEASE = "release"
    REVERT = "revert"
    CLOSE = "close"


@dataclass
class TransitionResult:
    """Result of a transition attempt."""
    success: bool
    from_status: Optional[Status] = None
    to_status: Optional[Status] = None
    workflow_type: Optional[WorkflowType] = None
    version_bump: Optional[str] = None  # None, "minor", "major"
    archives_version: bool = False
    clears_owner: bool = False
    error_message: Optional[str] = None


@dataclass
class StatusTransition:
    """
    Represents a single valid status transition in the workflow.

    Attributes:
        from_status: Starting status
        to_status: Destination status
        action: The action that triggers this transition
        workflow_type: The workflow phase (for task generation)
        requires_assignment: Whether user must be assigned to perform this action
        version_bump: Version change on transition ("minor", "major", or None)
        archives_version: Whether to archive the current version
        clears_owner: Whether to clear the responsible_user
        for_executable: True if this transition is for executable docs only
        for_non_executable: True if this transition is for non-executable docs only
        requires_phase: ExecutionPhase required (for executable post-release detection)
    """
    from_status: Status
    to_status: Status
    action: Action
    workflow_type: Optional[WorkflowType] = None
    requires_assignment: bool = False
    version_bump: Optional[str] = None
    archives_version: bool = False
    clears_owner: bool = False
    for_executable: Optional[bool] = None  # None = both, True = exec only, False = non-exec only
    requires_phase: Optional[ExecutionPhase] = None


# =============================================================================
# Transition Definitions
# =============================================================================

# All valid transitions in the system, organized by action
WORKFLOW_TRANSITIONS: List[StatusTransition] = [
    # --- ROUTE TO REVIEW ---
    # Non-executable: DRAFT -> IN_REVIEW
    StatusTransition(
        from_status=Status.DRAFT,
        to_status=Status.IN_REVIEW,
        action=Action.ROUTE_REVIEW,
        workflow_type=WorkflowType.REVIEW,
        for_executable=False,
    ),
    # Executable pre-release: DRAFT -> IN_PRE_REVIEW
    StatusTransition(
        from_status=Status.DRAFT,
        to_status=Status.IN_PRE_REVIEW,
        action=Action.ROUTE_REVIEW,
        workflow_type=WorkflowType.PRE_REVIEW,
        for_executable=True,
        requires_phase=ExecutionPhase.PRE_RELEASE,
    ),
    # Executable post-release: DRAFT/IN_EXECUTION -> IN_POST_REVIEW
    StatusTransition(
        from_status=Status.DRAFT,
        to_status=Status.IN_POST_REVIEW,
        action=Action.ROUTE_REVIEW,
        workflow_type=WorkflowType.POST_REVIEW,
        for_executable=True,
        requires_phase=ExecutionPhase.POST_RELEASE,
    ),
    StatusTransition(
        from_status=Status.IN_EXECUTION,
        to_status=Status.IN_POST_REVIEW,
        action=Action.ROUTE_REVIEW,
        workflow_type=WorkflowType.POST_REVIEW,
        for_executable=True,
        requires_phase=ExecutionPhase.POST_RELEASE,
    ),

    # --- ROUTE TO APPROVAL ---
    # Non-executable: REVIEWED -> IN_APPROVAL
    StatusTransition(
        from_status=Status.REVIEWED,
        to_status=Status.IN_APPROVAL,
        action=Action.ROUTE_APPROVAL,
        workflow_type=WorkflowType.APPROVAL,
        for_executable=False,
    ),
    # Executable pre-release: PRE_REVIEWED -> IN_PRE_APPROVAL
    StatusTransition(
        from_status=Status.PRE_REVIEWED,
        to_status=Status.IN_PRE_APPROVAL,
        action=Action.ROUTE_APPROVAL,
        workflow_type=WorkflowType.PRE_APPROVAL,
        for_executable=True,
        requires_phase=ExecutionPhase.PRE_RELEASE,
    ),
    # Executable post-release: POST_REVIEWED -> IN_POST_APPROVAL
    StatusTransition(
        from_status=Status.POST_REVIEWED,
        to_status=Status.IN_POST_APPROVAL,
        action=Action.ROUTE_APPROVAL,
        workflow_type=WorkflowType.POST_APPROVAL,
        for_executable=True,
        requires_phase=ExecutionPhase.POST_RELEASE,
    ),

    # --- REVIEW COMPLETION ---
    # Non-executable
    StatusTransition(
        from_status=Status.IN_REVIEW,
        to_status=Status.REVIEWED,
        action=Action.REVIEW,
        workflow_type=WorkflowType.REVIEW,
        requires_assignment=True,
        for_executable=False,
    ),
    # Executable pre-release
    StatusTransition(
        from_status=Status.IN_PRE_REVIEW,
        to_status=Status.PRE_REVIEWED,
        action=Action.REVIEW,
        workflow_type=WorkflowType.PRE_REVIEW,
        requires_assignment=True,
        for_executable=True,
    ),
    # Executable post-release
    StatusTransition(
        from_status=Status.IN_POST_REVIEW,
        to_status=Status.POST_REVIEWED,
        action=Action.REVIEW,
        workflow_type=WorkflowType.POST_REVIEW,
        requires_assignment=True,
        for_executable=True,
    ),

    # --- APPROVAL ---
    # Non-executable: IN_APPROVAL -> APPROVED -> EFFECTIVE
    StatusTransition(
        from_status=Status.IN_APPROVAL,
        to_status=Status.APPROVED,
        action=Action.APPROVE,
        workflow_type=WorkflowType.APPROVAL,
        requires_assignment=True,
        version_bump="major",
        archives_version=True,
        for_executable=False,
    ),
    # Executable pre-release: IN_PRE_APPROVAL -> PRE_APPROVED
    StatusTransition(
        from_status=Status.IN_PRE_APPROVAL,
        to_status=Status.PRE_APPROVED,
        action=Action.APPROVE,
        workflow_type=WorkflowType.PRE_APPROVAL,
        requires_assignment=True,
        version_bump="major",
        archives_version=True,
        for_executable=True,
    ),
    # Executable post-release: IN_POST_APPROVAL -> POST_APPROVED
    StatusTransition(
        from_status=Status.IN_POST_APPROVAL,
        to_status=Status.POST_APPROVED,
        action=Action.APPROVE,
        workflow_type=WorkflowType.POST_APPROVAL,
        requires_assignment=True,
        version_bump="major",
        archives_version=True,
        for_executable=True,
    ),

    # --- REJECTION ---
    # Non-executable: IN_APPROVAL -> REVIEWED
    StatusTransition(
        from_status=Status.IN_APPROVAL,
        to_status=Status.REVIEWED,
        action=Action.REJECT,
        workflow_type=WorkflowType.APPROVAL,
        requires_assignment=True,
        for_executable=False,
    ),
    # Executable pre-release: IN_PRE_APPROVAL -> PRE_REVIEWED
    StatusTransition(
        from_status=Status.IN_PRE_APPROVAL,
        to_status=Status.PRE_REVIEWED,
        action=Action.REJECT,
        workflow_type=WorkflowType.PRE_APPROVAL,
        requires_assignment=True,
        for_executable=True,
    ),
    # Executable post-release: IN_POST_APPROVAL -> POST_REVIEWED
    StatusTransition(
        from_status=Status.IN_POST_APPROVAL,
        to_status=Status.POST_REVIEWED,
        action=Action.REJECT,
        workflow_type=WorkflowType.POST_APPROVAL,
        requires_assignment=True,
        for_executable=True,
    ),

    # --- RELEASE ---
    # PRE_APPROVED -> IN_EXECUTION
    StatusTransition(
        from_status=Status.PRE_APPROVED,
        to_status=Status.IN_EXECUTION,
        action=Action.RELEASE,
        for_executable=True,
    ),

    # --- REVERT ---
    # POST_REVIEWED -> IN_EXECUTION (revert back to execution)
    StatusTransition(
        from_status=Status.POST_REVIEWED,
        to_status=Status.IN_EXECUTION,
        action=Action.REVERT,
        for_executable=True,
    ),

    # --- CLOSE ---
    # POST_APPROVED -> CLOSED
    StatusTransition(
        from_status=Status.POST_APPROVED,
        to_status=Status.CLOSED,
        action=Action.CLOSE,
        clears_owner=True,
        for_executable=True,
    ),
]


class WorkflowEngine:
    """
    Central workflow state machine engine.

    Provides methods to:
    - Validate whether a transition is allowed
    - Find the appropriate transition for a given action and context
    - Get workflow type for task generation
    """

    def __init__(self, transitions: Optional[List[StatusTransition]] = None):
        """Initialize with transition definitions."""
        self._transitions = transitions or WORKFLOW_TRANSITIONS
        self._build_index()

    def _build_index(self) -> None:
        """Build lookup indexes for fast transition queries."""
        # Index by (from_status, action)
        self._by_status_action: Dict[Tuple[Status, Action], List[StatusTransition]] = {}
        for t in self._transitions:
            key = (t.from_status, t.action)
            if key not in self._by_status_action:
                self._by_status_action[key] = []
            self._by_status_action[key].append(t)

    def get_transition(
        self,
        current_status: Status,
        action: Action,
        is_executable: bool,
        execution_phase: Optional[ExecutionPhase] = None,
    ) -> TransitionResult:
        """
        Find the appropriate transition for the given context.

        Args:
            current_status: Current document status
            action: Action being performed
            is_executable: Whether document is executable
            execution_phase: Current execution phase (for executable docs)

        Returns:
            TransitionResult with success=True if valid transition found
        """
        key = (current_status, action)
        candidates = self._by_status_action.get(key, [])

        if not candidates:
            return TransitionResult(
                success=False,
                error_message=f"No transition defined for {action.value} from {current_status.value}"
            )

        # Filter by executable/non-executable
        matching = []
        for t in candidates:
            # Check executable match
            if t.for_executable is not None:
                if t.for_executable != is_executable:
                    continue

            # Check phase match for executable docs
            if t.requires_phase is not None:
                if not is_executable:
                    continue
                # Infer phase from status if not explicitly provided
                inferred_phase = execution_phase
                if inferred_phase is None:
                    inferred_phase = self._infer_phase(current_status)
                if inferred_phase != t.requires_phase:
                    continue

            matching.append(t)

        if not matching:
            # Build helpful error message
            if is_executable:
                phase_str = execution_phase.value if execution_phase else "unknown"
                return TransitionResult(
                    success=False,
                    error_message=f"Cannot {action.value} from {current_status.value} "
                                  f"(executable, phase={phase_str})"
                )
            else:
                return TransitionResult(
                    success=False,
                    error_message=f"Cannot {action.value} from {current_status.value} (non-executable)"
                )

        if len(matching) > 1:
            # Ambiguous - should not happen with well-defined transitions
            return TransitionResult(
                success=False,
                error_message=f"Ambiguous transition: {len(matching)} candidates for "
                              f"{action.value} from {current_status.value}"
            )

        # Found exactly one match
        t = matching[0]
        return TransitionResult(
            success=True,
            from_status=t.from_status,
            to_status=t.to_status,
            workflow_type=t.workflow_type,
            version_bump=t.version_bump,
            archives_version=t.archives_version,
            clears_owner=t.clears_owner,
        )

    def _infer_phase(self, status: Status) -> Optional[ExecutionPhase]:
        """Infer execution phase from status."""
        pre_release_statuses = {
            Status.DRAFT, Status.IN_PRE_REVIEW, Status.PRE_REVIEWED,
            Status.IN_PRE_APPROVAL, Status.PRE_APPROVED
        }
        post_release_statuses = {
            Status.IN_EXECUTION, Status.IN_POST_REVIEW, Status.POST_REVIEWED,
            Status.IN_POST_APPROVAL, Status.POST_APPROVED, Status.CLOSED
        }

        if status in pre_release_statuses:
            return ExecutionPhase.PRE_RELEASE
        elif status in post_release_statuses:
            return ExecutionPhase.POST_RELEASE
        return None

    def is_review_status(self, status: Status) -> bool:
        """Check if status is a review state."""
        return status in {Status.IN_REVIEW, Status.IN_PRE_REVIEW, Status.IN_POST_REVIEW}

    def is_approval_status(self, status: Status) -> bool:
        """Check if status is an approval state."""
        return status in {Status.IN_APPROVAL, Status.IN_PRE_APPROVAL, Status.IN_POST_APPROVAL}

    def get_reviewed_status(self, current_status: Status) -> Optional[Status]:
        """Get the REVIEWED status corresponding to current IN_*_REVIEW status."""
        status_map = {
            Status.IN_REVIEW: Status.REVIEWED,
            Status.IN_PRE_REVIEW: Status.PRE_REVIEWED,
            Status.IN_POST_REVIEW: Status.POST_REVIEWED,
        }
        return status_map.get(current_status)

    def get_approved_status(self, current_status: Status) -> Optional[Status]:
        """Get the APPROVED status corresponding to current IN_*_APPROVAL status."""
        status_map = {
            Status.IN_APPROVAL: Status.APPROVED,
            Status.IN_PRE_APPROVAL: Status.PRE_APPROVED,
            Status.IN_POST_APPROVAL: Status.POST_APPROVED,
        }
        return status_map.get(current_status)

    def get_rejection_target(self, current_status: Status) -> Optional[Status]:
        """Get the target status for rejection from current approval status."""
        status_map = {
            Status.IN_APPROVAL: Status.REVIEWED,
            Status.IN_PRE_APPROVAL: Status.PRE_REVIEWED,
            Status.IN_POST_APPROVAL: Status.POST_REVIEWED,
        }
        return status_map.get(current_status)

    def validate_transition(self, from_status: Status, to_status: Status) -> bool:
        """
        Check if a raw status transition is valid per TRANSITIONS config.

        This is a low-level check against the existing TRANSITIONS dict.
        """
        allowed = TRANSITIONS.get(from_status, [])
        return to_status in allowed

    def get_workflow_type_for_status(
        self,
        status: Status,
        is_executable: bool
    ) -> Optional[WorkflowType]:
        """Determine workflow type based on current status."""
        if status == Status.IN_REVIEW:
            return WorkflowType.REVIEW
        elif status == Status.IN_APPROVAL:
            return WorkflowType.APPROVAL
        elif status == Status.IN_PRE_REVIEW:
            return WorkflowType.PRE_REVIEW
        elif status == Status.IN_PRE_APPROVAL:
            return WorkflowType.PRE_APPROVAL
        elif status == Status.IN_POST_REVIEW:
            return WorkflowType.POST_REVIEW
        elif status == Status.IN_POST_APPROVAL:
            return WorkflowType.POST_APPROVAL
        return None


# Global engine instance
_engine: Optional[WorkflowEngine] = None


def get_workflow_engine() -> WorkflowEngine:
    """Get the global workflow engine instance."""
    global _engine
    if _engine is None:
        _engine = WorkflowEngine()
    return _engine
