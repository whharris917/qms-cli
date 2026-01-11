"""
Test Workflow Engine

Tests for the WorkflowEngine state machine that governs document transitions.

Created as part of CR-026: QMS CLI Extensibility Refactoring
"""
import sys
from pathlib import Path

import pytest

# Add qms-cli to path for imports
QMS_CLI_DIR = Path(__file__).parent.parent
if str(QMS_CLI_DIR) not in sys.path:
    sys.path.insert(0, str(QMS_CLI_DIR))

from qms_config import Status
from workflow import (
    WorkflowEngine, WorkflowType, ExecutionPhase, Action,
    StatusTransition, TransitionResult, get_workflow_engine, WORKFLOW_TRANSITIONS
)


class TestWorkflowEngineRouteReview:
    """Tests for routing documents to review."""

    def test_non_executable_draft_to_in_review(self):
        """Non-executable document: DRAFT -> IN_REVIEW."""
        engine = get_workflow_engine()
        result = engine.get_transition(
            current_status=Status.DRAFT,
            action=Action.ROUTE_REVIEW,
            is_executable=False,
        )
        assert result.success
        assert result.from_status == Status.DRAFT
        assert result.to_status == Status.IN_REVIEW
        assert result.workflow_type == WorkflowType.REVIEW

    def test_executable_pre_release_draft_to_pre_review(self):
        """Executable document pre-release: DRAFT -> IN_PRE_REVIEW."""
        engine = get_workflow_engine()
        result = engine.get_transition(
            current_status=Status.DRAFT,
            action=Action.ROUTE_REVIEW,
            is_executable=True,
            execution_phase=ExecutionPhase.PRE_RELEASE,
        )
        assert result.success
        assert result.from_status == Status.DRAFT
        assert result.to_status == Status.IN_PRE_REVIEW
        assert result.workflow_type == WorkflowType.PRE_REVIEW

    def test_executable_post_release_draft_to_post_review(self):
        """Executable document post-release: DRAFT -> IN_POST_REVIEW."""
        engine = get_workflow_engine()
        result = engine.get_transition(
            current_status=Status.DRAFT,
            action=Action.ROUTE_REVIEW,
            is_executable=True,
            execution_phase=ExecutionPhase.POST_RELEASE,
        )
        assert result.success
        assert result.from_status == Status.DRAFT
        assert result.to_status == Status.IN_POST_REVIEW
        assert result.workflow_type == WorkflowType.POST_REVIEW

    def test_executable_in_execution_to_post_review(self):
        """Executable document: IN_EXECUTION -> IN_POST_REVIEW."""
        engine = get_workflow_engine()
        result = engine.get_transition(
            current_status=Status.IN_EXECUTION,
            action=Action.ROUTE_REVIEW,
            is_executable=True,
            execution_phase=ExecutionPhase.POST_RELEASE,
        )
        assert result.success
        assert result.to_status == Status.IN_POST_REVIEW
        assert result.workflow_type == WorkflowType.POST_REVIEW


class TestWorkflowEngineRouteApproval:
    """Tests for routing documents to approval."""

    def test_non_executable_reviewed_to_in_approval(self):
        """Non-executable: REVIEWED -> IN_APPROVAL."""
        engine = get_workflow_engine()
        result = engine.get_transition(
            current_status=Status.REVIEWED,
            action=Action.ROUTE_APPROVAL,
            is_executable=False,
        )
        assert result.success
        assert result.to_status == Status.IN_APPROVAL
        assert result.workflow_type == WorkflowType.APPROVAL

    def test_executable_pre_reviewed_to_pre_approval(self):
        """Executable pre-release: PRE_REVIEWED -> IN_PRE_APPROVAL."""
        engine = get_workflow_engine()
        result = engine.get_transition(
            current_status=Status.PRE_REVIEWED,
            action=Action.ROUTE_APPROVAL,
            is_executable=True,
            execution_phase=ExecutionPhase.PRE_RELEASE,
        )
        assert result.success
        assert result.to_status == Status.IN_PRE_APPROVAL
        assert result.workflow_type == WorkflowType.PRE_APPROVAL

    def test_executable_post_reviewed_to_post_approval(self):
        """Executable post-release: POST_REVIEWED -> IN_POST_APPROVAL."""
        engine = get_workflow_engine()
        result = engine.get_transition(
            current_status=Status.POST_REVIEWED,
            action=Action.ROUTE_APPROVAL,
            is_executable=True,
            execution_phase=ExecutionPhase.POST_RELEASE,
        )
        assert result.success
        assert result.to_status == Status.IN_POST_APPROVAL
        assert result.workflow_type == WorkflowType.POST_APPROVAL


class TestWorkflowEngineReviewCompletion:
    """Tests for review completion transitions."""

    def test_non_executable_in_review_to_reviewed(self):
        """Non-executable: IN_REVIEW -> REVIEWED."""
        engine = get_workflow_engine()
        result = engine.get_transition(
            current_status=Status.IN_REVIEW,
            action=Action.REVIEW,
            is_executable=False,
        )
        assert result.success
        assert result.to_status == Status.REVIEWED
        assert result.workflow_type == WorkflowType.REVIEW
        # Review completion does not bump version
        assert result.version_bump is None

    def test_executable_pre_review_to_pre_reviewed(self):
        """Executable: IN_PRE_REVIEW -> PRE_REVIEWED."""
        engine = get_workflow_engine()
        result = engine.get_transition(
            current_status=Status.IN_PRE_REVIEW,
            action=Action.REVIEW,
            is_executable=True,
        )
        assert result.success
        assert result.to_status == Status.PRE_REVIEWED

    def test_executable_post_review_to_post_reviewed(self):
        """Executable: IN_POST_REVIEW -> POST_REVIEWED."""
        engine = get_workflow_engine()
        result = engine.get_transition(
            current_status=Status.IN_POST_REVIEW,
            action=Action.REVIEW,
            is_executable=True,
        )
        assert result.success
        assert result.to_status == Status.POST_REVIEWED


class TestWorkflowEngineApproval:
    """Tests for approval transitions."""

    def test_non_executable_approval_bumps_major_version(self):
        """Non-executable approval bumps major version."""
        engine = get_workflow_engine()
        result = engine.get_transition(
            current_status=Status.IN_APPROVAL,
            action=Action.APPROVE,
            is_executable=False,
        )
        assert result.success
        assert result.to_status == Status.APPROVED
        assert result.version_bump == "major"
        assert result.archives_version is True

    def test_executable_pre_approval_bumps_major_version(self):
        """Executable pre-approval bumps major version."""
        engine = get_workflow_engine()
        result = engine.get_transition(
            current_status=Status.IN_PRE_APPROVAL,
            action=Action.APPROVE,
            is_executable=True,
        )
        assert result.success
        assert result.to_status == Status.PRE_APPROVED
        assert result.version_bump == "major"
        assert result.archives_version is True

    def test_executable_post_approval_bumps_major_version(self):
        """Executable post-approval bumps major version."""
        engine = get_workflow_engine()
        result = engine.get_transition(
            current_status=Status.IN_POST_APPROVAL,
            action=Action.APPROVE,
            is_executable=True,
        )
        assert result.success
        assert result.to_status == Status.POST_APPROVED
        assert result.version_bump == "major"


class TestWorkflowEngineRejection:
    """Tests for rejection transitions."""

    def test_non_executable_rejection_returns_to_reviewed(self):
        """Non-executable rejection: IN_APPROVAL -> REVIEWED."""
        engine = get_workflow_engine()
        result = engine.get_transition(
            current_status=Status.IN_APPROVAL,
            action=Action.REJECT,
            is_executable=False,
        )
        assert result.success
        assert result.to_status == Status.REVIEWED

    def test_executable_pre_rejection_returns_to_pre_reviewed(self):
        """Executable pre-release rejection: IN_PRE_APPROVAL -> PRE_REVIEWED."""
        engine = get_workflow_engine()
        result = engine.get_transition(
            current_status=Status.IN_PRE_APPROVAL,
            action=Action.REJECT,
            is_executable=True,
        )
        assert result.success
        assert result.to_status == Status.PRE_REVIEWED

    def test_executable_post_rejection_returns_to_post_reviewed(self):
        """Executable post-release rejection: IN_POST_APPROVAL -> POST_REVIEWED."""
        engine = get_workflow_engine()
        result = engine.get_transition(
            current_status=Status.IN_POST_APPROVAL,
            action=Action.REJECT,
            is_executable=True,
        )
        assert result.success
        assert result.to_status == Status.POST_REVIEWED


class TestWorkflowEngineRelease:
    """Tests for release transition."""

    def test_release_pre_approved_to_in_execution(self):
        """Release: PRE_APPROVED -> IN_EXECUTION."""
        engine = get_workflow_engine()
        result = engine.get_transition(
            current_status=Status.PRE_APPROVED,
            action=Action.RELEASE,
            is_executable=True,
        )
        assert result.success
        assert result.to_status == Status.IN_EXECUTION

    def test_release_not_valid_for_non_executable(self):
        """Release is not valid for non-executable documents."""
        engine = get_workflow_engine()
        result = engine.get_transition(
            current_status=Status.APPROVED,
            action=Action.RELEASE,
            is_executable=False,
        )
        assert not result.success
        assert "No transition" in result.error_message or "Cannot" in result.error_message


class TestWorkflowEngineRevert:
    """Tests for revert transition."""

    def test_revert_post_reviewed_to_in_execution(self):
        """Revert: POST_REVIEWED -> IN_EXECUTION."""
        engine = get_workflow_engine()
        result = engine.get_transition(
            current_status=Status.POST_REVIEWED,
            action=Action.REVERT,
            is_executable=True,
        )
        assert result.success
        assert result.to_status == Status.IN_EXECUTION


class TestWorkflowEngineClose:
    """Tests for close transition."""

    def test_close_post_approved_to_closed(self):
        """Close: POST_APPROVED -> CLOSED."""
        engine = get_workflow_engine()
        result = engine.get_transition(
            current_status=Status.POST_APPROVED,
            action=Action.CLOSE,
            is_executable=True,
        )
        assert result.success
        assert result.to_status == Status.CLOSED
        assert result.clears_owner is True


class TestWorkflowEnginePhaseInference:
    """Tests for execution phase inference."""

    def test_infer_pre_release_from_draft(self):
        """DRAFT status infers pre-release phase."""
        engine = get_workflow_engine()
        phase = engine._infer_phase(Status.DRAFT)
        assert phase == ExecutionPhase.PRE_RELEASE

    def test_infer_pre_release_from_pre_reviewed(self):
        """PRE_REVIEWED status infers pre-release phase."""
        engine = get_workflow_engine()
        phase = engine._infer_phase(Status.PRE_REVIEWED)
        assert phase == ExecutionPhase.PRE_RELEASE

    def test_infer_post_release_from_in_execution(self):
        """IN_EXECUTION status infers post-release phase."""
        engine = get_workflow_engine()
        phase = engine._infer_phase(Status.IN_EXECUTION)
        assert phase == ExecutionPhase.POST_RELEASE

    def test_infer_post_release_from_post_reviewed(self):
        """POST_REVIEWED status infers post-release phase."""
        engine = get_workflow_engine()
        phase = engine._infer_phase(Status.POST_REVIEWED)
        assert phase == ExecutionPhase.POST_RELEASE


class TestWorkflowEngineStatusHelpers:
    """Tests for status helper methods."""

    def test_is_review_status(self):
        """Test is_review_status helper."""
        engine = get_workflow_engine()
        assert engine.is_review_status(Status.IN_REVIEW)
        assert engine.is_review_status(Status.IN_PRE_REVIEW)
        assert engine.is_review_status(Status.IN_POST_REVIEW)
        assert not engine.is_review_status(Status.IN_APPROVAL)
        assert not engine.is_review_status(Status.DRAFT)

    def test_is_approval_status(self):
        """Test is_approval_status helper."""
        engine = get_workflow_engine()
        assert engine.is_approval_status(Status.IN_APPROVAL)
        assert engine.is_approval_status(Status.IN_PRE_APPROVAL)
        assert engine.is_approval_status(Status.IN_POST_APPROVAL)
        assert not engine.is_approval_status(Status.IN_REVIEW)
        assert not engine.is_approval_status(Status.DRAFT)

    def test_get_reviewed_status(self):
        """Test get_reviewed_status mapping."""
        engine = get_workflow_engine()
        assert engine.get_reviewed_status(Status.IN_REVIEW) == Status.REVIEWED
        assert engine.get_reviewed_status(Status.IN_PRE_REVIEW) == Status.PRE_REVIEWED
        assert engine.get_reviewed_status(Status.IN_POST_REVIEW) == Status.POST_REVIEWED
        assert engine.get_reviewed_status(Status.DRAFT) is None

    def test_get_approved_status(self):
        """Test get_approved_status mapping."""
        engine = get_workflow_engine()
        assert engine.get_approved_status(Status.IN_APPROVAL) == Status.APPROVED
        assert engine.get_approved_status(Status.IN_PRE_APPROVAL) == Status.PRE_APPROVED
        assert engine.get_approved_status(Status.IN_POST_APPROVAL) == Status.POST_APPROVED
        assert engine.get_approved_status(Status.DRAFT) is None

    def test_get_rejection_target(self):
        """Test get_rejection_target mapping."""
        engine = get_workflow_engine()
        assert engine.get_rejection_target(Status.IN_APPROVAL) == Status.REVIEWED
        assert engine.get_rejection_target(Status.IN_PRE_APPROVAL) == Status.PRE_REVIEWED
        assert engine.get_rejection_target(Status.IN_POST_APPROVAL) == Status.POST_REVIEWED


class TestWorkflowEngineValidation:
    """Tests for transition validation."""

    def test_validate_valid_transition(self):
        """Valid transition returns True."""
        engine = get_workflow_engine()
        assert engine.validate_transition(Status.DRAFT, Status.IN_REVIEW)
        assert engine.validate_transition(Status.DRAFT, Status.IN_PRE_REVIEW)
        assert engine.validate_transition(Status.IN_REVIEW, Status.REVIEWED)

    def test_validate_invalid_transition(self):
        """Invalid transition returns False."""
        engine = get_workflow_engine()
        assert not engine.validate_transition(Status.DRAFT, Status.APPROVED)
        assert not engine.validate_transition(Status.EFFECTIVE, Status.DRAFT)

    def test_invalid_action_returns_error(self):
        """Invalid action from status returns error."""
        engine = get_workflow_engine()
        result = engine.get_transition(
            current_status=Status.EFFECTIVE,
            action=Action.ROUTE_REVIEW,
            is_executable=False,
        )
        assert not result.success
        assert result.error_message is not None


class TestWorkflowEngineGetWorkflowType:
    """Tests for workflow type determination."""

    def test_get_workflow_type_for_review_statuses(self):
        """Get workflow type for review statuses."""
        engine = get_workflow_engine()
        assert engine.get_workflow_type_for_status(Status.IN_REVIEW, False) == WorkflowType.REVIEW
        assert engine.get_workflow_type_for_status(Status.IN_PRE_REVIEW, True) == WorkflowType.PRE_REVIEW
        assert engine.get_workflow_type_for_status(Status.IN_POST_REVIEW, True) == WorkflowType.POST_REVIEW

    def test_get_workflow_type_for_approval_statuses(self):
        """Get workflow type for approval statuses."""
        engine = get_workflow_engine()
        assert engine.get_workflow_type_for_status(Status.IN_APPROVAL, False) == WorkflowType.APPROVAL
        assert engine.get_workflow_type_for_status(Status.IN_PRE_APPROVAL, True) == WorkflowType.PRE_APPROVAL
        assert engine.get_workflow_type_for_status(Status.IN_POST_APPROVAL, True) == WorkflowType.POST_APPROVAL

    def test_get_workflow_type_returns_none_for_other_statuses(self):
        """Non-workflow statuses return None."""
        engine = get_workflow_engine()
        assert engine.get_workflow_type_for_status(Status.DRAFT, False) is None
        assert engine.get_workflow_type_for_status(Status.EFFECTIVE, False) is None


class TestTransitionDefinitions:
    """Tests for the transition definitions themselves."""

    def test_all_transitions_have_required_fields(self):
        """All transitions have required from_status, to_status, action."""
        for t in WORKFLOW_TRANSITIONS:
            assert t.from_status is not None
            assert t.to_status is not None
            assert t.action is not None

    def test_review_actions_require_assignment(self):
        """Review actions should require assignment."""
        for t in WORKFLOW_TRANSITIONS:
            if t.action == Action.REVIEW:
                assert t.requires_assignment is True, f"Review transition {t.from_status} -> {t.to_status} should require assignment"

    def test_approval_actions_require_assignment(self):
        """Approval actions should require assignment."""
        for t in WORKFLOW_TRANSITIONS:
            if t.action == Action.APPROVE:
                assert t.requires_assignment is True, f"Approval transition {t.from_status} -> {t.to_status} should require assignment"

    def test_approval_actions_bump_major_version(self):
        """Approval actions should bump major version."""
        for t in WORKFLOW_TRANSITIONS:
            if t.action == Action.APPROVE:
                assert t.version_bump == "major", f"Approval transition {t.from_status} -> {t.to_status} should bump major version"
