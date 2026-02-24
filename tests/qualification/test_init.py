"""
QMS CLI Qualification Tests: Initialization and User Management

Tests for the init command and user management functionality.
Verifies requirements: INIT-001 through INIT-012, USER-001, USER-002, USER-003
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
    """
    Execute qms init command and return result.

    By default, passes --root and --yes to bypass marker detection and
    confirmation prompt. Tests for those specific behaviors use
    run_qms_init_raw() instead.
    """
    qms_cli = Path(__file__).parent.parent.parent / "qms.py"
    arg_list = list(args)

    # If caller didn't specify --root, add it pointing to project_path
    if "--root" not in arg_list:
        arg_list.extend(["--root", str(project_path)])

    # If caller didn't specify --yes or -y, add --yes
    if "--yes" not in arg_list and "-y" not in arg_list:
        arg_list.append("--yes")

    cmd = [sys.executable, str(qms_cli), "init"] + arg_list
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=project_path
    )
    return result


def run_qms_init_raw(cwd, *args):
    """
    Execute qms init command without any default flags.

    Used for testing marker detection, confirmation prompt, and no-context behavior.
    """
    qms_cli = Path(__file__).parent.parent.parent / "qms.py"
    cmd = [sys.executable, str(qms_cli), "init"] + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd
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

    Verifies: REQ-INIT-001, REQ-INIT-002, REQ-INIT-003
    """
    # [REQ-INIT-001] Init creates config file
    result = run_qms_init(clean_project)
    assert result.returncode == 0, f"Init should succeed: {result.stderr}"

    config_path = clean_project / "qms.config.json"
    assert config_path.exists(), "qms.config.json should be created"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert config.get("version") == "1.0", "Config should have version 1.0"

    # [REQ-INIT-002] QMS directories created (no SOP directory)
    assert (clean_project / "QMS" / "CR").is_dir(), "QMS/CR should exist"
    assert (clean_project / "QMS" / "INV").is_dir(), "QMS/INV should exist"
    assert (clean_project / "QMS" / "TEMPLATE").is_dir(), "QMS/TEMPLATE should exist"
    assert (clean_project / "QMS" / ".meta").is_dir(), "QMS/.meta should exist"
    assert (clean_project / "QMS" / ".audit").is_dir(), "QMS/.audit should exist"
    assert (clean_project / "QMS" / ".archive").is_dir(), "QMS/.archive should exist"

    # [REQ-INIT-003] User workspaces for all default users including tu
    for user in ["lead", "claude", "qa", "tu"]:
        workspace = clean_project / ".claude" / "users" / user / "workspace"
        inbox = clean_project / ".claude" / "users" / user / "inbox"
        assert workspace.is_dir(), f"Workspace for {user} should exist"
        assert inbox.is_dir(), f"Inbox for {user} should exist"


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


def test_init_seeds_agents(clean_project):
    """
    Verify init seeds qa and tu agent definitions.

    Verifies: REQ-INIT-004
    """
    run_qms_init(clean_project)

    # [REQ-INIT-004] QA agent is seeded with quality group
    qa_agent = clean_project / ".claude" / "agents" / "qa.md"
    assert qa_agent.exists(), "qa.md agent should be seeded"
    qa_content = qa_agent.read_text(encoding="utf-8")
    assert "group: quality" in qa_content, "QA agent should have group: quality"

    # [REQ-INIT-004] TU agent is seeded with reviewer group
    tu_agent = clean_project / ".claude" / "agents" / "tu.md"
    assert tu_agent.exists(), "tu.md agent should be seeded"
    tu_content = tu_agent.read_text(encoding="utf-8")
    assert "group: reviewer" in tu_content, "TU agent should have group: reviewer"


# ============================================================================
# Test: Init Command Safety Checks
# ============================================================================

def test_init_blocked_by_existing_qms(clean_project):
    """
    Verify init is blocked when QMS/ directory exists.

    Verifies: REQ-INIT-009
    """
    # Create blocking structure
    (clean_project / "QMS").mkdir()

    # [REQ-INIT-009] Init blocked by existing infrastructure
    result = run_qms_init(clean_project)
    assert result.returncode != 0, "Init should fail with existing QMS/"
    assert "QMS/" in result.stdout or "already exists" in result.stdout.lower(), \
        "Error should mention existing QMS/"


def test_init_blocked_by_existing_users(clean_project):
    """
    Verify init is blocked when .claude/users/ directory exists.

    Verifies: REQ-INIT-009
    """
    (clean_project / ".claude" / "users").mkdir(parents=True)

    result = run_qms_init(clean_project)
    assert result.returncode != 0, "Init should fail with existing .claude/users/"
    assert "users" in result.stdout.lower() or "already exists" in result.stdout.lower()


def test_init_blocked_by_existing_qa_agent(clean_project):
    """
    Verify init is blocked when .claude/agents/qa.md exists.

    Verifies: REQ-INIT-009
    """
    (clean_project / ".claude" / "agents").mkdir(parents=True)
    (clean_project / ".claude" / "agents" / "qa.md").write_text("# Existing agent")

    result = run_qms_init(clean_project)
    assert result.returncode != 0, "Init should fail with existing qa.md"
    assert "qa.md" in result.stdout.lower() or "already exists" in result.stdout.lower()


def test_init_blocked_by_existing_config(clean_project):
    """
    Verify init is blocked when qms.config.json exists.

    Verifies: REQ-INIT-009
    """
    (clean_project / "qms.config.json").write_text('{"version": "1.0"}')

    result = run_qms_init(clean_project)
    assert result.returncode != 0, "Init should fail with existing qms.config.json"
    assert "config" in result.stdout.lower() or "already exists" in result.stdout.lower()


def test_init_blocked_by_existing_claude_md(clean_project):
    """
    Verify init is blocked when CLAUDE.md exists.

    Verifies: REQ-INIT-009
    """
    (clean_project / "CLAUDE.md").write_text("# Existing CLAUDE.md")

    result = run_qms_init(clean_project)
    assert result.returncode != 0, "Init should fail with existing CLAUDE.md"
    assert "CLAUDE.md" in result.stdout or "already exists" in result.stdout.lower()


# ============================================================================
# Test: Hooks and CLAUDE.md Seeding
# ============================================================================

def test_init_seeds_hooks(clean_project):
    """
    Verify init seeds .claude/hooks/ with write guard.

    Verifies: REQ-INIT-007
    """
    run_qms_init(clean_project)

    # [REQ-INIT-007] Hooks directory is seeded
    hooks_dir = clean_project / ".claude" / "hooks"
    assert hooks_dir.is_dir(), ".claude/hooks/ should exist"

    # Write guard hook must be present
    write_guard = hooks_dir / "qms-write-guard.py"
    assert write_guard.exists(), "qms-write-guard.py should be seeded"

    # Verify it blocks QMS-managed directories
    content = write_guard.read_text(encoding="utf-8")
    assert "QMS/.meta/" in content, "Write guard should protect QMS/.meta/"
    assert "QMS/.audit/" in content, "Write guard should protect QMS/.audit/"
    assert "QMS/.archive/" in content, "Write guard should protect QMS/.archive/"


def test_init_seeds_claude_md(clean_project):
    """
    Verify init seeds CLAUDE.md at project root.

    Verifies: REQ-INIT-008
    """
    run_qms_init(clean_project)

    # [REQ-INIT-008] CLAUDE.md is seeded
    claude_md = clean_project / "CLAUDE.md"
    assert claude_md.exists(), "CLAUDE.md should be seeded"

    content = claude_md.read_text(encoding="utf-8")
    assert "QMS" in content, "CLAUDE.md should mention QMS"
    assert "claude" in content.lower(), "CLAUDE.md should reference claude identity"


# ============================================================================
# Test: Marker Detection (CR-104)
# ============================================================================

def test_init_detects_marker_in_parent(tmp_path):
    """
    Verify init finds .claude-qms marker one level up and uses parent as root.

    Verifies: REQ-INIT-011
    """
    # Set up: parent has marker, child simulates qms-cli/
    parent = tmp_path / "project"
    parent.mkdir()
    (parent / ".claude-qms").touch()
    child = parent / "qms-cli"
    child.mkdir()

    # Run init from child with --yes (no --root)
    result = run_qms_init_raw(child, "--yes")
    assert result.returncode == 0, f"Init should succeed with marker in parent: {result.stderr}\n{result.stdout}"

    # Verify structure created in parent, not child
    assert (parent / "qms.config.json").exists(), "Config should be in parent (marker location)"
    assert (parent / "QMS" / "CR").is_dir(), "QMS/CR should be in parent"
    assert not (child / "qms.config.json").exists(), "Config should NOT be in child"


def test_init_no_context_fails(tmp_path):
    """
    Verify init fails with helpful error when no marker and no --root.

    Verifies: REQ-INIT-011
    """
    # No marker file anywhere, no --root flag
    result = run_qms_init_raw(tmp_path)
    assert result.returncode != 0, "Init should fail without marker or --root"
    assert "Cannot determine project root" in result.stdout, \
        "Error should explain the problem"
    assert ".claude-qms" in result.stdout, \
        "Error should mention the marker file"
    assert "--root" in result.stdout, \
        "Error should mention the --root alternative"


# ============================================================================
# Test: Confirmation Prompt (CR-104)
# ============================================================================

def test_init_confirmation_aborts_on_no(tmp_path):
    """
    Verify init aborts when user responds 'N' to confirmation prompt.

    Verifies: REQ-INIT-012
    """
    qms_cli = Path(__file__).parent.parent.parent / "qms.py"
    cmd = [sys.executable, str(qms_cli), "init", "--root", str(tmp_path)]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        input="N\n",
        cwd=tmp_path
    )
    assert result.returncode != 0, "Init should abort when user says N"
    assert "Aborted" in result.stdout, "Should print 'Aborted'"
    assert not (tmp_path / "qms.config.json").exists(), \
        "No files should be created after abort"


def test_init_confirmation_aborts_on_empty(tmp_path):
    """
    Verify init aborts when user provides empty response (default is N).

    Verifies: REQ-INIT-012
    """
    qms_cli = Path(__file__).parent.parent.parent / "qms.py"
    cmd = [sys.executable, str(qms_cli), "init", "--root", str(tmp_path)]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        input="\n",
        cwd=tmp_path
    )
    assert result.returncode != 0, "Init should abort on empty response (default N)"
    assert not (tmp_path / "qms.config.json").exists(), \
        "No files should be created after abort"


def test_init_confirmation_proceeds_on_yes(tmp_path):
    """
    Verify init proceeds when user responds 'y' to confirmation prompt.

    Verifies: REQ-INIT-012
    """
    qms_cli = Path(__file__).parent.parent.parent / "qms.py"
    cmd = [sys.executable, str(qms_cli), "init", "--root", str(tmp_path)]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        input="y\n",
        cwd=tmp_path
    )
    assert result.returncode == 0, f"Init should proceed on 'y': {result.stderr}\n{result.stdout}"
    assert (tmp_path / "qms.config.json").exists(), \
        "Files should be created after confirmation"


def test_init_confirmation_shows_artifact_list(tmp_path):
    """
    Verify confirmation prompt lists the artifacts that will be created.

    Verifies: REQ-INIT-012
    """
    qms_cli = Path(__file__).parent.parent.parent / "qms.py"
    cmd = [sys.executable, str(qms_cli), "init", "--root", str(tmp_path)]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        input="N\n",
        cwd=tmp_path
    )
    # Even though we abort, the prompt should have been shown
    assert "qms.config.json" in result.stdout, "Prompt should list qms.config.json"
    assert "QMS/" in result.stdout, "Prompt should list QMS/"
    assert "CLAUDE.md" in result.stdout, "Prompt should list CLAUDE.md"
    assert ".claude/users/" in result.stdout, "Prompt should list .claude/users/"
    assert "Proceed?" in result.stdout, "Prompt should ask to proceed"


def test_init_yes_flag_skips_confirmation(clean_project):
    """
    Verify --yes flag skips the confirmation prompt entirely.

    Verifies: REQ-INIT-012
    """
    result = run_qms_init(clean_project)  # run_qms_init adds --yes by default
    assert result.returncode == 0, f"Init with --yes should succeed: {result.stderr}"
    assert "Proceed?" not in result.stdout, \
        "Confirmation prompt should not appear with --yes"
    assert (clean_project / "qms.config.json").exists(), \
        "Files should be created with --yes"


def test_init_aborts_on_eof(tmp_path):
    """
    Verify init aborts gracefully when stdin is closed (EOF).

    Verifies: REQ-INIT-012
    """
    qms_cli = Path(__file__).parent.parent.parent / "qms.py"
    cmd = [sys.executable, str(qms_cli), "init", "--root", str(tmp_path)]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        input="",  # EOF immediately
        cwd=tmp_path
    )
    assert result.returncode != 0, "Init should abort on EOF"
    assert not (tmp_path / "qms.config.json").exists(), \
        "No files should be created after EOF abort"


# ============================================================================
# Test: --root with Marker Placement (CR-104)
# ============================================================================

def test_init_root_places_marker(tmp_path):
    """
    Verify --root places .claude-qms marker in target directory.

    Verifies: REQ-INIT-010
    """
    target = tmp_path / "my-project"
    target.mkdir()

    result = run_qms_init(tmp_path, "--root", str(target), "--yes")
    assert result.returncode == 0, f"Init with --root should succeed: {result.stderr}"

    # Marker should be placed
    assert (target / ".claude-qms").exists(), \
        ".claude-qms marker should be placed by --root"

    # QMS structure should be in target
    assert (target / "qms.config.json").exists(), \
        "Config should be in --root target"
    assert (target / "QMS" / "CR").is_dir(), \
        "QMS/CR should be in --root target"


def test_init_root_does_not_duplicate_marker(tmp_path):
    """
    Verify --root does not create a duplicate marker if one already exists.

    Verifies: REQ-INIT-010
    """
    target = tmp_path / "my-project"
    target.mkdir()
    (target / ".claude-qms").touch()

    result = run_qms_init(tmp_path, "--root", str(target), "--yes")
    assert result.returncode == 0, f"Init should succeed: {result.stderr}"

    # Should not print "Created: .claude-qms" since it already existed
    assert ".claude-qms" not in result.stdout or "Created" not in result.stdout.split(".claude-qms")[0].split("\n")[-1], \
        "Should not re-create existing marker"


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

    Verifies: REQ-INIT-010
    """
    # Create a different target directory
    target = tmp_path_factory.mktemp("target_project")

    # Run init with --root flag
    result = run_qms_init(clean_project, "--root", str(target), "--yes")
    assert result.returncode == 0, f"Init with --root should succeed: {result.stderr}"

    # Verify structure created in target, not clean_project
    assert not (clean_project / "qms.config.json").exists(), \
        "Config should NOT be in cwd"
    assert (target / "qms.config.json").exists(), \
        "Config should be in --root target"
    assert (target / "QMS" / "CR").is_dir(), \
        "QMS/CR should be in --root target"
    assert (target / "CLAUDE.md").exists(), \
        "CLAUDE.md should be in --root target"


# ============================================================================
# Test: Documentation Directories Exist in Distribution
# ============================================================================

def test_docs_directory_exists():
    """
    Verify qms-cli ships with a docs/ directory containing software documentation.

    Verifies: REQ-INIT-006
    """
    qms_cli_root = Path(__file__).parent.parent.parent
    docs_dir = qms_cli_root / "docs"

    assert docs_dir.is_dir(), "docs/ directory should exist in qms-cli"
    assert (docs_dir / "README.md").exists(), "docs/README.md should exist"
    assert (docs_dir / "cli-reference.md").exists(), "docs/cli-reference.md should exist"
    assert (docs_dir / "getting-started.md").exists(), "docs/getting-started.md should exist"


def test_manual_directory_exists():
    """
    Verify qms-cli ships with a manual/ directory containing QMS operational documentation.

    Verifies: REQ-INIT-006
    """
    qms_cli_root = Path(__file__).parent.parent.parent
    manual_dir = qms_cli_root / "manual"

    assert manual_dir.is_dir(), "manual/ directory should exist in qms-cli"
    assert (manual_dir / "QMS-Policy.md").exists(), "manual/QMS-Policy.md should exist"
    assert (manual_dir / "QMS-Glossary.md").exists(), "manual/QMS-Glossary.md should exist"
    assert (manual_dir / "START_HERE.md").exists(), "manual/START_HERE.md should exist"
    assert (manual_dir / "guides").is_dir(), "manual/guides/ should exist"
    assert (manual_dir / "types").is_dir(), "manual/types/ should exist"


def test_init_does_not_seed_qms_docs(clean_project):
    """
    Verify init does NOT create QMS-Docs/ at the project root.

    Verifies: REQ-INIT-006 (documentation lives in qms-cli, not seeded)
    """
    run_qms_init(clean_project)
    assert not (clean_project / "QMS-Docs").exists(), \
        "QMS-Docs/ should NOT be created by init"
