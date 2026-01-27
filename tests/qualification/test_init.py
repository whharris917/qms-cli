"""
QMS CLI Qualification Tests: Initialization and User Management

Tests for the init command and user management functionality.
Verifies requirements: INIT-001, INIT-002, INIT-003, USER-001, USER-002, USER-003
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest


# ============================================================================
# Helper Functions
# ============================================================================

def run_qms_init(project_path, *args):
    """Execute qms init command and return result."""
    qms_cli = Path(__file__).parent.parent.parent / "qms.py"
    cmd = [sys.executable, str(qms_cli), "init"] + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=project_path
    )
    return result


def run_qms(project_path, user, *args):
    """Execute a QMS CLI command and return result."""
    qms_cli = Path(__file__).parent.parent.parent / "qms.py"
    cmd = [sys.executable, str(qms_cli), "--user", user] + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=project_path
    )
    return result


def read_meta(project_path, doc_id, doc_type):
    """Read .meta JSON file for a document."""
    meta_path = project_path / "QMS" / ".meta" / doc_type / f"{doc_id}.json"
    if not meta_path.exists():
        return None
    return json.loads(meta_path.read_text(encoding="utf-8"))


def read_audit(project_path, doc_id, doc_type):
    """Read .audit JSONL file for a document."""
    audit_path = project_path / "QMS" / ".audit" / doc_type / f"{doc_id}.jsonl"
    if not audit_path.exists():
        return []
    entries = []
    for line in audit_path.read_text(encoding="utf-8").strip().split("\n"):
        if line:
            entries.append(json.loads(line))
    return entries


# ============================================================================
# Fixture: Clean Project (no pre-existing QMS structure)
# ============================================================================

@pytest.fixture
def clean_project(tmp_path):
    """
    Create a clean temporary directory for init testing.
    Unlike temp_project, this has NO pre-existing QMS structure.
    """
    return tmp_path


# ============================================================================
# Test: Init Command Success
# ============================================================================

def test_init_creates_complete_structure(clean_project):
    """
    Verify init creates complete QMS infrastructure on clean directory.

    Verifies: REQ-INIT-001
    """
    # [REQ-INIT-001] Init creates complete structure
    result = run_qms_init(clean_project)
    assert result.returncode == 0, f"Init should succeed: {result.stderr}"

    # Verify qms.config.json created
    config_path = clean_project / "qms.config.json"
    assert config_path.exists(), "qms.config.json should be created"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert config.get("version") == "1.0", "Config should have version 1.0"

    # Verify QMS directories created
    assert (clean_project / "QMS" / "SOP").is_dir(), "QMS/SOP should exist"
    assert (clean_project / "QMS" / "CR").is_dir(), "QMS/CR should exist"
    assert (clean_project / "QMS" / "INV").is_dir(), "QMS/INV should exist"
    assert (clean_project / "QMS" / "TEMPLATE").is_dir(), "QMS/TEMPLATE should exist"
    assert (clean_project / "QMS" / ".meta").is_dir(), "QMS/.meta should exist"
    assert (clean_project / "QMS" / ".audit").is_dir(), "QMS/.audit should exist"
    assert (clean_project / "QMS" / ".archive").is_dir(), "QMS/.archive should exist"

    # Verify user workspaces created
    for user in ["lead", "claude", "qa"]:
        workspace = clean_project / ".claude" / "users" / user / "workspace"
        inbox = clean_project / ".claude" / "users" / user / "inbox"
        assert workspace.is_dir(), f"Workspace for {user} should exist"
        assert inbox.is_dir(), f"Inbox for {user} should exist"


def test_init_seeds_sops(clean_project):
    """
    Verify init seeds SOPs with correct metadata.

    Verifies: REQ-INIT-002
    """
    run_qms_init(clean_project)

    # [REQ-INIT-002] SOPs are seeded
    sop_dir = clean_project / "QMS" / "SOP"
    seeded_sops = list(sop_dir.glob("SOP-*.md"))
    assert len(seeded_sops) >= 1, "At least one SOP should be seeded"

    # Check first SOP has correct metadata
    sop_001_meta = read_meta(clean_project, "SOP-001", "SOP")
    assert sop_001_meta is not None, "SOP-001 should have metadata"
    assert sop_001_meta.get("version") == "1.0", "SOP should be v1.0"
    assert sop_001_meta.get("status") == "EFFECTIVE", "SOP should be EFFECTIVE"

    # Check audit trail
    sop_001_audit = read_audit(clean_project, "SOP-001", "SOP")
    assert len(sop_001_audit) >= 1, "SOP-001 should have audit entry"
    assert sop_001_audit[0].get("action") == "seed", "First audit action should be seed"


def test_init_seeds_templates(clean_project):
    """
    Verify init seeds document templates.

    Verifies: REQ-INIT-002
    """
    run_qms_init(clean_project)

    # [REQ-INIT-002] Templates are seeded
    template_dir = clean_project / "QMS" / "TEMPLATE"
    seeded_templates = list(template_dir.glob("TEMPLATE-*.md"))
    assert len(seeded_templates) >= 1, "At least one template should be seeded"


def test_init_seeds_qa_agent(clean_project):
    """
    Verify init seeds qa agent definition.

    Verifies: REQ-INIT-002
    """
    run_qms_init(clean_project)

    # [REQ-INIT-002] QA agent is seeded
    qa_agent = clean_project / ".claude" / "agents" / "qa.md"
    assert qa_agent.exists(), "qa.md agent should be seeded"

    # Verify agent has group frontmatter
    content = qa_agent.read_text(encoding="utf-8")
    assert "group:" in content, "QA agent should have group in frontmatter"


# ============================================================================
# Test: Init Command Safety Checks
# ============================================================================

def test_init_blocked_by_existing_qms(clean_project):
    """
    Verify init is blocked when QMS/ directory exists.

    Verifies: REQ-INIT-003
    """
    # Create blocking structure
    (clean_project / "QMS").mkdir()

    # [REQ-INIT-003] Init blocked by existing infrastructure
    result = run_qms_init(clean_project)
    assert result.returncode != 0, "Init should fail with existing QMS/"
    assert "QMS/" in result.stdout or "already exists" in result.stdout.lower(), \
        "Error should mention existing QMS/"


def test_init_blocked_by_existing_users(clean_project):
    """
    Verify init is blocked when .claude/users/ directory exists.

    Verifies: REQ-INIT-003
    """
    (clean_project / ".claude" / "users").mkdir(parents=True)

    result = run_qms_init(clean_project)
    assert result.returncode != 0, "Init should fail with existing .claude/users/"
    assert "users" in result.stdout.lower() or "already exists" in result.stdout.lower()


def test_init_blocked_by_existing_qa_agent(clean_project):
    """
    Verify init is blocked when .claude/agents/qa.md exists.

    Verifies: REQ-INIT-003
    """
    (clean_project / ".claude" / "agents").mkdir(parents=True)
    (clean_project / ".claude" / "agents" / "qa.md").write_text("# Existing agent")

    result = run_qms_init(clean_project)
    assert result.returncode != 0, "Init should fail with existing qa.md"
    assert "qa.md" in result.stdout.lower() or "already exists" in result.stdout.lower()


def test_init_blocked_by_existing_config(clean_project):
    """
    Verify init is blocked when qms.config.json exists.

    Verifies: REQ-INIT-003
    """
    (clean_project / "qms.config.json").write_text('{"version": "1.0"}')

    result = run_qms_init(clean_project)
    assert result.returncode != 0, "Init should fail with existing qms.config.json"
    assert "config" in result.stdout.lower() or "already exists" in result.stdout.lower()


# ============================================================================
# Test: User Management
# ============================================================================

def test_user_add_creates_structure(clean_project):
    """
    Verify user --add creates agent file and directories.

    Verifies: REQ-USER-001
    """
    # Initialize first
    run_qms_init(clean_project)

    # [REQ-USER-001] User add creates structure
    result = run_qms(clean_project, "claude", "user", "--add", "alice", "--group", "reviewer")
    assert result.returncode == 0, f"User add should succeed: {result.stderr}"

    # Verify agent file created
    agent_path = clean_project / ".claude" / "agents" / "alice.md"
    assert agent_path.exists(), "Agent file should be created"
    content = agent_path.read_text(encoding="utf-8")
    assert "group: reviewer" in content, "Agent should have correct group"

    # Verify workspace/inbox created
    assert (clean_project / ".claude" / "users" / "alice" / "workspace").is_dir()
    assert (clean_project / ".claude" / "users" / "alice" / "inbox").is_dir()


def test_user_add_requires_admin(clean_project):
    """
    Verify only administrators can add users.

    Verifies: REQ-USER-002
    """
    run_qms_init(clean_project)

    # [REQ-USER-002] Non-admins cannot add users
    result = run_qms(clean_project, "qa", "user", "--add", "bob", "--group", "reviewer")
    assert result.returncode != 0, "QA (non-admin) should not be able to add users"
    assert "permission" in result.stdout.lower() or "denied" in result.stdout.lower()


def test_hardcoded_admins_work(clean_project):
    """
    Verify hardcoded administrators (lead, claude) can operate without agent files.

    Verifies: REQ-USER-003
    """
    run_qms_init(clean_project)

    # [REQ-USER-003] Hardcoded admins work without agent files
    # Note: lead and claude don't have agent files but should work
    result = run_qms(clean_project, "lead", "create", "CR", "--title", "Test CR")
    assert result.returncode == 0, f"Lead should be able to create: {result.stderr}"

    result = run_qms(clean_project, "claude", "create", "CR", "--title", "Test CR 2")
    assert result.returncode == 0, f"Claude should be able to create: {result.stderr}"


def test_unknown_user_error(clean_project):
    """
    Verify unknown users get helpful error message.

    Verifies: REQ-USER-003
    """
    run_qms_init(clean_project)

    # [REQ-USER-003] Unknown users get helpful error
    result = run_qms(clean_project, "nobody", "create", "CR", "--title", "Test")
    assert result.returncode != 0, "Unknown user should fail"
    assert "not found" in result.stdout.lower() or "unknown" in result.stdout.lower() or \
           "create" in result.stdout.lower() and "agent" in result.stdout.lower()


def test_agent_group_assignment(clean_project):
    """
    Verify user groups are read from agent file frontmatter.

    Verifies: REQ-USER-001
    """
    run_qms_init(clean_project)

    # QA agent was seeded with group: quality
    # Verify QA can perform QA-specific actions (like assign)
    run_qms(clean_project, "claude", "create", "CR", "--title", "Test CR")
    run_qms(clean_project, "claude", "checkin", "CR-001")
    run_qms(clean_project, "claude", "route", "CR-001", "--review")

    # QA (quality group) should be able to assign
    result = run_qms(clean_project, "qa", "assign", "CR-001", "--assignees", "lead")
    assert result.returncode == 0, f"QA should be able to assign: {result.stderr}"


# ============================================================================
# Test: Full Lifecycle in Initialized Project
# ============================================================================

def test_full_document_lifecycle_in_initialized_project(clean_project):
    """
    Verify complete document lifecycle works in an initialized project.

    Verifies: REQ-INIT-001, REQ-INIT-002
    """
    # Initialize the project
    run_qms_init(clean_project)

    # Create a CR (document is automatically checked out to creator)
    result = run_qms(clean_project, "claude", "create", "CR", "--title", "Test Change")
    assert result.returncode == 0, "Should create CR"

    # Check in (document was checked out during creation)
    result = run_qms(clean_project, "claude", "checkin", "CR-001")
    assert result.returncode == 0, "Should checkin CR"

    # Route for review
    result = run_qms(clean_project, "claude", "route", "CR-001", "--review")
    assert result.returncode == 0, "Should route for review"

    # QA assigns
    result = run_qms(clean_project, "qa", "assign", "CR-001", "--assignees", "lead")
    assert result.returncode == 0, "QA should assign"

    # Verify document status (CRs use IN_PRE_REVIEW for executable workflow)
    meta = read_meta(clean_project, "CR-001", "CR")
    assert meta.get("status") == "IN_PRE_REVIEW", "CR should be IN_PRE_REVIEW"


# ============================================================================
# Test: Init with --root flag
# ============================================================================

def test_init_with_root_flag(clean_project, tmp_path_factory):
    """
    Verify init --root creates structure in specified directory.

    Verifies: REQ-INIT-001
    """
    # Create a different target directory
    target = tmp_path_factory.mktemp("target_project")

    # Run init with --root flag
    result = run_qms_init(clean_project, "--root", str(target))
    assert result.returncode == 0, f"Init with --root should succeed: {result.stderr}"

    # Verify structure created in target, not clean_project
    assert not (clean_project / "qms.config.json").exists(), \
        "Config should NOT be in cwd"
    assert (target / "qms.config.json").exists(), \
        "Config should be in --root target"
    assert (target / "QMS" / "SOP").is_dir(), \
        "QMS/SOP should be in --root target"
