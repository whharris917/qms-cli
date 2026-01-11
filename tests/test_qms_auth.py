"""
Unit tests for QMS CLI authentication and permission functions.

Tests cover:
- get_user_group(): Determine which group a user belongs to
- check_permission(): Verify user can execute a command
- verify_user_identity(): Validate user is a known QMS user
- verify_folder_access(): Check user can access another user's folder
"""
import pytest


class TestGetUserGroup:
    """Tests for get_user_group() function."""

    def test_initiators(self, qms_module):
        """Lead and claude should be in initiators group."""
        assert qms_module.get_user_group("lead") == "initiators"
        assert qms_module.get_user_group("claude") == "initiators"

    def test_qa_group(self, qms_module):
        """QA user should be in qa group."""
        assert qms_module.get_user_group("qa") == "qa"

    def test_reviewers(self, qms_module):
        """TU and BU users should be in reviewers group."""
        assert qms_module.get_user_group("tu_ui") == "reviewers"
        assert qms_module.get_user_group("tu_scene") == "reviewers"
        assert qms_module.get_user_group("tu_sketch") == "reviewers"
        assert qms_module.get_user_group("tu_sim") == "reviewers"
        assert qms_module.get_user_group("bu") == "reviewers"

    def test_unknown_user(self, qms_module):
        """Unknown users should return 'unknown' group."""
        assert qms_module.get_user_group("random_user") == "unknown"


class TestCheckPermission:
    """Tests for check_permission() function."""

    def test_initiator_can_create(self, qms_module):
        """Initiators should be able to create documents."""
        allowed, msg = qms_module.check_permission("claude", "create")
        assert allowed is True

        allowed, msg = qms_module.check_permission("lead", "create")
        assert allowed is True

    def test_reviewer_cannot_create(self, qms_module):
        """Reviewers should not be able to create documents."""
        allowed, msg = qms_module.check_permission("tu_ui", "create")
        assert allowed is False
        assert "Permission Denied" in msg

    def test_qa_can_assign(self, qms_module):
        """QA should be able to assign reviewers."""
        allowed, msg = qms_module.check_permission("qa", "assign")
        assert allowed is True

    def test_initiator_cannot_assign(self, qms_module):
        """Initiators should not be able to assign reviewers."""
        allowed, msg = qms_module.check_permission("claude", "assign")
        assert allowed is False

    def test_owner_only_command(self, qms_module):
        """Owner-only commands should check document ownership."""
        # Owner can release
        allowed, msg = qms_module.check_permission("claude", "release", doc_owner="claude")
        assert allowed is True

        # Non-owner cannot release (unless also initiator)
        allowed, msg = qms_module.check_permission("qa", "release", doc_owner="claude")
        assert allowed is False

    def test_initiators_can_act_on_each_other(self, qms_module):
        """Initiators should be able to act on each other's documents."""
        # Lead can release claude's document
        allowed, msg = qms_module.check_permission("lead", "release", doc_owner="claude")
        assert allowed is True

        # Claude can release lead's document
        allowed, msg = qms_module.check_permission("claude", "release", doc_owner="lead")
        assert allowed is True

    def test_assigned_only_command(self, qms_module):
        """Assigned-only commands should check assignment."""
        # Assigned user can review
        allowed, msg = qms_module.check_permission(
            "qa", "review", assigned_users=["qa", "tu_ui"]
        )
        assert allowed is True

        # Non-assigned user cannot review
        allowed, msg = qms_module.check_permission(
            "tu_sim", "review", assigned_users=["qa", "tu_ui"]
        )
        assert allowed is False
        assert "not assigned" in msg.lower()

    def test_qa_can_approve(self, qms_module):
        """QA should be able to approve when assigned."""
        allowed, msg = qms_module.check_permission(
            "qa", "approve", assigned_users=["qa"]
        )
        assert allowed is True

    def test_reviewer_can_approve_when_assigned(self, qms_module):
        """Reviewers should be able to approve when assigned."""
        allowed, msg = qms_module.check_permission(
            "tu_ui", "approve", assigned_users=["qa", "tu_ui"]
        )
        assert allowed is True

    def test_unknown_command_allowed(self, qms_module):
        """Unknown commands should be allowed (fail open for extensibility)."""
        allowed, msg = qms_module.check_permission("claude", "unknown_command")
        assert allowed is True


class TestVerifyUserIdentity:
    """Tests for verify_user_identity() function."""

    def test_valid_users(self, qms_module, capsys):
        """Valid users should return True."""
        assert qms_module.verify_user_identity("claude") is True
        assert qms_module.verify_user_identity("lead") is True
        assert qms_module.verify_user_identity("qa") is True
        assert qms_module.verify_user_identity("tu_ui") is True
        assert qms_module.verify_user_identity("bu") is True

    def test_invalid_user(self, qms_module, capsys):
        """Invalid users should return False and print error."""
        assert qms_module.verify_user_identity("unknown_user") is False
        captured = capsys.readouterr()
        assert "not a valid QMS user" in captured.out


class TestVerifyFolderAccess:
    """Tests for verify_folder_access() function."""

    def test_user_can_access_own_folder(self, qms_module, capsys):
        """Users should be able to access their own folders."""
        assert qms_module.verify_folder_access("claude", "claude", "view inbox") is True

    def test_user_cannot_access_other_folder(self, qms_module, capsys):
        """Users should not be able to access other users' folders."""
        assert qms_module.verify_folder_access("claude", "qa", "view inbox") is False
        captured = capsys.readouterr()
        assert "Access denied" in captured.out
