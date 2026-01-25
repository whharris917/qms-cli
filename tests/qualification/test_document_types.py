"""
QMS CLI Qualification Tests: Document Types and Creation

Tests for document type support, ID generation, and parent-child relationships.
Verifies requirements: DOC-001, DOC-002, DOC-004, DOC-005, DOC-010, DOC-011, DOC-012
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest


# ============================================================================
# Helper Functions
# ============================================================================

def run_qms(temp_project, user, *args):
    """Execute a QMS CLI command and return result."""
    qms_cli = Path(__file__).parent.parent.parent / "qms.py"
    cmd = [sys.executable, str(qms_cli), "--user", user] + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=temp_project
    )
    return result


def read_meta(temp_project, doc_id, doc_type):
    """Read .meta JSON file for a document."""
    meta_path = temp_project / "QMS" / ".meta" / doc_type / f"{doc_id}.json"
    if not meta_path.exists():
        return None
    return json.loads(meta_path.read_text(encoding="utf-8"))


# ============================================================================
# Test: Supported Document Types
# ============================================================================

def test_create_sop(temp_project):
    """
    Create SOP document type.

    Verifies: REQ-DOC-001
    """
    # [REQ-DOC-001] Create SOP
    result = run_qms(temp_project, "claude", "create", "SOP", "--title", "Test SOP")
    assert result.returncode == 0, f"Create SOP failed: {result.stderr}"

    # Verify file exists with correct ID format
    assert (temp_project / "QMS" / "SOP" / "SOP-001-draft.md").exists()

    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["doc_type"] == "SOP"
    assert meta["executable"] == False


def test_create_cr(temp_project):
    """
    Create CR document type (executable, folder-per-doc).

    Verifies: REQ-DOC-001
    """
    # [REQ-DOC-001] Create CR
    result = run_qms(temp_project, "claude", "create", "CR", "--title", "Test CR")
    assert result.returncode == 0, f"Create CR failed: {result.stderr}"

    # Verify folder structure
    cr_folder = temp_project / "QMS" / "CR" / "CR-001"
    assert cr_folder.exists(), "CR folder not created"
    assert (cr_folder / "CR-001-draft.md").exists()

    meta = read_meta(temp_project, "CR-001", "CR")
    assert meta["doc_type"] == "CR"
    assert meta["executable"] == True


def test_create_inv(temp_project):
    """
    Create INV document type (executable, folder-per-doc).

    Verifies: REQ-DOC-001
    """
    # [REQ-DOC-001] Create INV
    result = run_qms(temp_project, "claude", "create", "INV", "--title", "Test Investigation")
    assert result.returncode == 0, f"Create INV failed: {result.stderr}"

    # Verify folder structure
    inv_folder = temp_project / "QMS" / "INV" / "INV-001"
    assert inv_folder.exists(), "INV folder not created"
    assert (inv_folder / "INV-001-draft.md").exists()

    meta = read_meta(temp_project, "INV-001", "INV")
    assert meta["doc_type"] == "INV"
    assert meta["executable"] == True


# ============================================================================
# Test: Child Document Relationships
# ============================================================================

def test_create_tp_under_cr(temp_project):
    """
    TP is created as a child of CR, stored within CR's folder.
    CR-034 CC-007: TP now uses sequential format CR-001-TP-001.

    Verifies: REQ-DOC-002
    """
    # Create parent CR first
    run_qms(temp_project, "claude", "create", "CR", "--title", "Parent CR")
    run_qms(temp_project, "claude", "checkin", "CR-001")

    # [REQ-DOC-002] Create TP under CR (now uses sequential ID)
    result = run_qms(temp_project, "claude", "create", "TP", "--parent", "CR-001",
                     "--title", "Test Protocol")
    assert result.returncode == 0, f"Create TP failed: {result.stderr}"

    # Verify TP is in CR's folder with sequential ID
    cr_folder = temp_project / "QMS" / "CR" / "CR-001"
    assert (cr_folder / "CR-001-TP-001-draft.md").exists(), "TP should be in CR folder with sequential ID"

    # Verify ID format
    meta = read_meta(temp_project, "CR-001-TP-001", "TP")
    assert meta is not None, "TP metadata should exist"
    assert meta["doc_type"] == "TP"


def test_create_var_under_cr(temp_project):
    """
    VAR is created as a child of CR, stored within CR's folder.

    Verifies: REQ-DOC-002, REQ-DOC-005
    """
    # Create parent CR first
    run_qms(temp_project, "claude", "create", "CR", "--title", "CR for VAR")
    run_qms(temp_project, "claude", "checkin", "CR-001")

    # [REQ-DOC-002] [REQ-DOC-005] Create VAR under CR
    result = run_qms(temp_project, "claude", "create", "VAR", "--parent", "CR-001",
                     "--title", "Variance Report 1")
    assert result.returncode == 0, f"Create VAR failed: {result.stderr}"

    # Verify VAR is in CR's folder
    cr_folder = temp_project / "QMS" / "CR" / "CR-001"
    assert (cr_folder / "CR-001-VAR-001-draft.md").exists(), "VAR should be in CR folder"

    # Create second VAR - should be CR-001-VAR-002
    result = run_qms(temp_project, "claude", "create", "VAR", "--parent", "CR-001",
                     "--title", "Variance Report 2")
    assert result.returncode == 0, f"Create second VAR failed: {result.stderr}"
    assert (cr_folder / "CR-001-VAR-002-draft.md").exists(), "Second VAR should be CR-001-VAR-002"


def test_create_var_under_inv(temp_project):
    """
    VAR can also be created as a child of INV.

    Verifies: REQ-DOC-002
    """
    # Create parent INV first (create command auto-creates folder structure)
    result = run_qms(temp_project, "claude", "create", "INV", "--title", "INV for VAR")
    assert result.returncode == 0, f"Create INV failed: {result.stderr}"
    run_qms(temp_project, "claude", "checkin", "INV-001")

    # [REQ-DOC-002] Create VAR under INV
    result = run_qms(temp_project, "claude", "create", "VAR", "--parent", "INV-001",
                     "--title", "INV Variance")
    assert result.returncode == 0, f"Create VAR under INV failed: {result.stderr}"

    # Verify VAR is in INV's folder with correct ID format
    inv_folder = temp_project / "QMS" / "INV" / "INV-001"
    assert (inv_folder / "INV-001-VAR-001-draft.md").exists(), "VAR should be in INV folder"


# ============================================================================
# Test: Sequential ID Generation
# ============================================================================

def test_sequential_id_generation(temp_project):
    """
    Document IDs are generated sequentially within each type.

    Verifies: REQ-DOC-004
    """
    # [REQ-DOC-004] Create multiple SOPs
    result = run_qms(temp_project, "claude", "create", "SOP", "--title", "First SOP")
    assert result.returncode == 0
    assert (temp_project / "QMS" / "SOP" / "SOP-001-draft.md").exists()

    result = run_qms(temp_project, "claude", "create", "SOP", "--title", "Second SOP")
    assert result.returncode == 0
    assert (temp_project / "QMS" / "SOP" / "SOP-002-draft.md").exists()

    result = run_qms(temp_project, "claude", "create", "SOP", "--title", "Third SOP")
    assert result.returncode == 0
    assert (temp_project / "QMS" / "SOP" / "SOP-003-draft.md").exists()

    # [REQ-DOC-004] Create CRs - separate sequence
    result = run_qms(temp_project, "claude", "create", "CR", "--title", "First CR")
    assert result.returncode == 0
    assert (temp_project / "QMS" / "CR" / "CR-001" / "CR-001-draft.md").exists()

    result = run_qms(temp_project, "claude", "create", "CR", "--title", "Second CR")
    assert result.returncode == 0
    assert (temp_project / "QMS" / "CR" / "CR-002" / "CR-002-draft.md").exists()


# ============================================================================
# Test: Child Document ID Generation
# ============================================================================

def test_child_id_generation(temp_project):
    """
    Child document IDs follow format {PARENT}-{TYPE}-NNN.

    Verifies: REQ-DOC-005
    """
    # Create parent CR
    run_qms(temp_project, "claude", "create", "CR", "--title", "Parent for IDs")
    run_qms(temp_project, "claude", "checkin", "CR-001")

    # [REQ-DOC-005] Create multiple VARs - should be sequential within parent
    run_qms(temp_project, "claude", "create", "VAR", "--parent", "CR-001", "--title", "VAR 1")
    run_qms(temp_project, "claude", "create", "VAR", "--parent", "CR-001", "--title", "VAR 2")
    run_qms(temp_project, "claude", "create", "VAR", "--parent", "CR-001", "--title", "VAR 3")

    cr_folder = temp_project / "QMS" / "CR" / "CR-001"
    assert (cr_folder / "CR-001-VAR-001-draft.md").exists()
    assert (cr_folder / "CR-001-VAR-002-draft.md").exists()
    assert (cr_folder / "CR-001-VAR-003-draft.md").exists()

    # Create second CR and add VARs - should start at 001 for that parent
    run_qms(temp_project, "claude", "create", "CR", "--title", "Second Parent")
    run_qms(temp_project, "claude", "checkin", "CR-002")
    run_qms(temp_project, "claude", "create", "VAR", "--parent", "CR-002", "--title", "VAR for CR-002")

    cr2_folder = temp_project / "QMS" / "CR" / "CR-002"
    assert (cr2_folder / "CR-002-VAR-001-draft.md").exists(), "VAR under CR-002 should be CR-002-VAR-001"


# ============================================================================
# Test: Cancel Restrictions
# ============================================================================

def test_cancel_v0_document(temp_project):
    """
    Documents with version < 1.0 can be cancelled.

    Verifies: REQ-DOC-010
    """
    # Create document at v0.1
    run_qms(temp_project, "claude", "create", "SOP", "--title", "To Be Cancelled")
    run_qms(temp_project, "claude", "checkin", "SOP-001")

    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["version"] == "0.1"

    # [REQ-DOC-010] Cancel with --confirm
    result = run_qms(temp_project, "claude", "cancel", "SOP-001", "--confirm")
    assert result.returncode == 0, f"Cancel failed: {result.stderr}"

    # Verify all files deleted
    assert not (temp_project / "QMS" / "SOP" / "SOP-001-draft.md").exists()
    assert read_meta(temp_project, "SOP-001", "SOP") is None


def test_cancel_blocked_for_v1(temp_project):
    """
    Documents with version >= 1.0 cannot be cancelled.

    Verifies: REQ-DOC-010
    """
    # Create and approve to v1.0
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Effective SOP")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")
    run_qms(temp_project, "qa", "review", "SOP-001", "--recommend", "--comment", "OK")
    run_qms(temp_project, "claude", "route", "SOP-001", "--approval")
    run_qms(temp_project, "qa", "approve", "SOP-001")

    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["version"] == "1.0"
    assert meta["status"] == "EFFECTIVE"

    # [REQ-DOC-010] Attempt cancel - should fail
    result = run_qms(temp_project, "claude", "cancel", "SOP-001", "--confirm")
    assert result.returncode != 0, "Cancel should be blocked for v1.0 documents"

    # Verify document still exists
    assert (temp_project / "QMS" / "SOP" / "SOP-001.md").exists()


# ============================================================================
# Test: Template Name-Based ID
# ============================================================================

def test_template_name_based_id(temp_project):
    """
    Template documents use name-based IDs instead of sequential numbers.

    Verifies: REQ-DOC-011
    """
    # Create template directory structure
    (temp_project / "QMS" / "TEMPLATE").mkdir(parents=True, exist_ok=True)
    (temp_project / "QMS" / ".meta" / "TEMPLATE").mkdir(parents=True, exist_ok=True)
    (temp_project / "QMS" / ".audit" / "TEMPLATE").mkdir(parents=True, exist_ok=True)

    # [REQ-DOC-011] Create template with name
    result = run_qms(temp_project, "claude", "create", "TEMPLATE", "--name", "CR",
                     "--title", "Change Record Template")
    assert result.returncode == 0, f"Create template failed: {result.stderr}"

    # Verify ID is TEMPLATE-CR, not TEMPLATE-001
    assert (temp_project / "QMS" / "TEMPLATE" / "TEMPLATE-CR-draft.md").exists()

    # Create another template with different name
    result = run_qms(temp_project, "claude", "create", "TEMPLATE", "--name", "SOP",
                     "--title", "SOP Template")
    assert result.returncode == 0
    assert (temp_project / "QMS" / "TEMPLATE" / "TEMPLATE-SOP-draft.md").exists()


# ============================================================================
# Test: SDLC Document Types
# ============================================================================

def test_sdlc_document_types(temp_project):
    """
    RS and RTM documents for configured SDLC namespaces.

    Verifies: REQ-DOC-012
    """
    # Create SDLC directory structure
    (temp_project / "QMS" / "SDLC-QMS").mkdir(parents=True, exist_ok=True)
    (temp_project / "QMS" / ".meta" / "QMS-RS").mkdir(parents=True, exist_ok=True)
    (temp_project / "QMS" / ".meta" / "QMS-RTM").mkdir(parents=True, exist_ok=True)
    (temp_project / "QMS" / ".audit" / "QMS-RS").mkdir(parents=True, exist_ok=True)
    (temp_project / "QMS" / ".audit" / "QMS-RTM").mkdir(parents=True, exist_ok=True)

    # [REQ-DOC-012] Create QMS-RS document
    result = run_qms(temp_project, "claude", "create", "QMS-RS",
                     "--title", "QMS Requirements Specification")
    assert result.returncode == 0, f"Create QMS-RS failed: {result.stderr}"

    # Verify ID and location
    assert (temp_project / "QMS" / "SDLC-QMS" / "SDLC-QMS-RS-draft.md").exists()

    # [REQ-DOC-012] Create QMS-RTM document
    result = run_qms(temp_project, "claude", "create", "QMS-RTM",
                     "--title", "QMS Requirements Traceability Matrix")
    assert result.returncode == 0, f"Create QMS-RTM failed: {result.stderr}"

    assert (temp_project / "QMS" / "SDLC-QMS" / "SDLC-QMS-RTM-draft.md").exists()


# ============================================================================
# Test: SDLC Namespace Registration
# ============================================================================

def test_sdlc_namespace_registration(temp_project):
    """
    SDLC namespaces can be registered via namespace add command.

    Verifies: REQ-DOC-013
    """
    # [REQ-DOC-013] Register a new namespace
    result = run_qms(temp_project, "claude", "namespace", "add", "MYPROJ")
    assert result.returncode == 0, f"Namespace add failed: {result.stderr}"

    # Verify directory structure created
    assert (temp_project / "QMS" / "SDLC-MYPROJ").exists(), "SDLC-MYPROJ directory should be created"

    # Verify namespace is persisted in configuration
    config_path = temp_project / "QMS" / ".meta" / "sdlc_namespaces.json"
    assert config_path.exists(), "Namespace configuration should be persisted"

    import json
    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert "MYPROJ" in config, "MYPROJ namespace should be in persisted config"

    # Verify namespace appears in list
    result = run_qms(temp_project, "claude", "namespace", "list")
    assert "MYPROJ" in result.stdout, "Newly registered namespace should appear in list"


def test_sdlc_namespace_list(temp_project):
    """
    SDLC namespaces can be listed via namespace list command.

    Verifies: REQ-DOC-013
    """
    # [REQ-DOC-013] List namespaces - should show built-in namespaces
    result = run_qms(temp_project, "claude", "namespace", "list")
    assert result.returncode == 0, f"Namespace list failed: {result.stderr}"

    # Verify built-in namespaces appear
    assert "QMS" in result.stdout or "FLOW" in result.stdout, \
        "Built-in namespaces should be listed"


# ============================================================================
# Test: SDLC Document Identification
# ============================================================================

def test_sdlc_document_identification(temp_project):
    """
    SDLC documents are identified by SDLC-{NAMESPACE}-{TYPE} pattern.

    Verifies: REQ-DOC-014
    """
    # Create SDLC directory structure for FLOW namespace
    (temp_project / "QMS" / "SDLC-FLOW").mkdir(parents=True, exist_ok=True)
    (temp_project / "QMS" / ".meta" / "FLOW-RS").mkdir(parents=True, exist_ok=True)
    (temp_project / "QMS" / ".audit" / "FLOW-RS").mkdir(parents=True, exist_ok=True)

    # [REQ-DOC-014] Create FLOW-RS document
    result = run_qms(temp_project, "claude", "create", "FLOW-RS",
                     "--title", "Flow Requirements Specification")
    assert result.returncode == 0, f"Create FLOW-RS failed: {result.stderr}"

    # Verify document ID follows SDLC-{NAMESPACE}-{TYPE} pattern
    assert (temp_project / "QMS" / "SDLC-FLOW" / "SDLC-FLOW-RS-draft.md").exists()

    # Verify metadata has correct doc_id
    meta = read_meta(temp_project, "SDLC-FLOW-RS", "FLOW-RS")
    assert meta is not None, "Metadata should exist"
    assert meta["doc_id"] == "SDLC-FLOW-RS"


# ============================================================================
# Test: Folder-per-Document Storage
# ============================================================================

def test_folder_per_document_cr(temp_project):
    """
    CR documents use folder-per-document storage pattern.

    Verifies: REQ-DOC-012
    """
    # [REQ-DOC-012] Create CR
    result = run_qms(temp_project, "claude", "create", "CR", "--title", "Folder Test CR")
    assert result.returncode == 0

    # Verify folder structure QMS/CR/CR-001/CR-001-draft.md
    cr_folder = temp_project / "QMS" / "CR" / "CR-001"
    assert cr_folder.exists(), "CR should have dedicated folder"
    assert cr_folder.is_dir(), "CR-001 should be a directory"
    assert (cr_folder / "CR-001-draft.md").exists(), "CR draft should be inside folder"


def test_folder_per_document_inv(temp_project):
    """
    INV documents use folder-per-document storage pattern.

    Verifies: REQ-DOC-012
    """
    # [REQ-DOC-012] Create INV
    result = run_qms(temp_project, "claude", "create", "INV", "--title", "Folder Test INV")
    assert result.returncode == 0

    # Verify folder structure QMS/INV/INV-001/INV-001-draft.md
    inv_folder = temp_project / "QMS" / "INV" / "INV-001"
    assert inv_folder.exists(), "INV should have dedicated folder"
    assert inv_folder.is_dir(), "INV-001 should be a directory"
    assert (inv_folder / "INV-001-draft.md").exists(), "INV draft should be inside folder"


def test_child_documents_in_parent_folder(temp_project):
    """
    Child documents (TP, VAR, ER) are stored in parent's folder.

    Verifies: REQ-DOC-012
    """
    # Create parent CR
    run_qms(temp_project, "claude", "create", "CR", "--title", "Parent CR")
    run_qms(temp_project, "claude", "checkin", "CR-001")

    # [REQ-DOC-012] Create TP child - should be in CR-001 folder
    result = run_qms(temp_project, "claude", "create", "TP", "--parent", "CR-001",
                     "--title", "Test Protocol")
    assert result.returncode == 0

    cr_folder = temp_project / "QMS" / "CR" / "CR-001"
    assert (cr_folder / "CR-001-TP-001-draft.md").exists(), \
        "TP should be stored in parent CR's folder"


# ============================================================================
# Test: Cancel Restrictions - Checkout Blocked
# ============================================================================

def test_cancel_blocked_while_checked_out(temp_project):
    """
    Cancel is rejected while document is checked out.

    Verifies: REQ-DOC-010
    """
    # Create SOP (auto-checked out)
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Cancel Checkout Test")

    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["checked_out"] == True

    # [REQ-DOC-010] Cancel should be rejected while checked out
    result = run_qms(temp_project, "claude", "cancel", "SOP-001", "--confirm")
    assert result.returncode != 0, "Cancel should be rejected while document is checked out"

    # Verify document still exists
    assert (temp_project / "QMS" / "SOP" / "SOP-001-draft.md").exists()

    # Checkin and then cancel should work
    run_qms(temp_project, "claude", "checkin", "SOP-001")

    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["checked_out"] == False

    result = run_qms(temp_project, "claude", "cancel", "SOP-001", "--confirm")
    assert result.returncode == 0, "Cancel should succeed after checkin"


# ============================================================================
# Test: Cancel Cleanup
# ============================================================================

def test_cancel_cleans_workspace_and_inbox(temp_project):
    """
    Cancel removes workspace copies and inbox tasks.

    Verifies: REQ-DOC-010
    """
    # Create SOP and get it to IN_REVIEW (creates inbox tasks)
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Cancel Cleanup Test")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")

    # Verify task exists in qa's inbox
    result = run_qms(temp_project, "qa", "inbox")
    assert "SOP-001" in result.stdout, "Task should be in qa's inbox"

    # Checkout to create workspace copy
    run_qms(temp_project, "claude", "checkout", "SOP-001")
    workspace_path = temp_project / ".claude" / "users" / "claude" / "workspace" / "SOP-001.md"
    assert workspace_path.exists(), "Workspace copy should exist"

    # Checkin before cancel (required)
    run_qms(temp_project, "claude", "checkin", "SOP-001")

    # [REQ-DOC-010] Cancel document
    result = run_qms(temp_project, "claude", "cancel", "SOP-001", "--confirm")
    assert result.returncode == 0

    # Verify workspace copy removed (if it existed after checkin - which it shouldn't)
    assert not workspace_path.exists(), "Workspace copy should not exist after cancel"

    # Verify inbox tasks cleared
    result = run_qms(temp_project, "qa", "inbox")
    assert "SOP-001" not in result.stdout, "Inbox tasks should be cleared after cancel"

    # Verify document files removed
    assert not (temp_project / "QMS" / "SOP" / "SOP-001-draft.md").exists()


# ============================================================================
# Test: Checkout EFFECTIVE Creates Archive
# ============================================================================

def test_checkout_effective_creates_archive(temp_project):
    """
    Checkout of EFFECTIVE document archives current version and creates draft.

    Verifies: REQ-DOC-007
    """
    # Create SOP and get to EFFECTIVE
    run_qms(temp_project, "claude", "create", "SOP", "--title", "Checkout Archive Test")
    run_qms(temp_project, "claude", "checkin", "SOP-001")
    run_qms(temp_project, "claude", "route", "SOP-001", "--review")
    run_qms(temp_project, "qa", "review", "SOP-001", "--recommend", "--comment", "OK")
    run_qms(temp_project, "claude", "route", "SOP-001", "--approval")
    run_qms(temp_project, "qa", "approve", "SOP-001")

    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["status"] == "EFFECTIVE"
    assert meta["version"] == "1.0"

    # Verify effective document exists, draft doesn't
    assert (temp_project / "QMS" / "SOP" / "SOP-001.md").exists()
    assert not (temp_project / "QMS" / "SOP" / "SOP-001-draft.md").exists()

    # [REQ-DOC-007] Checkout EFFECTIVE document
    result = run_qms(temp_project, "claude", "checkout", "SOP-001")
    assert result.returncode == 0

    # Verify archive created (v1.0)
    archive_path = temp_project / "QMS" / ".archive" / "SOP" / "SOP-001-v1.0.md"
    assert archive_path.exists(), "Archive of v1.0 should be created"

    # Verify new draft created at N.1 version
    meta = read_meta(temp_project, "SOP-001", "SOP")
    assert meta["version"] == "1.1", "Version should be incremented to 1.1"
    assert meta["status"] == "DRAFT", "Status should be DRAFT"

    # Verify draft file exists
    assert (temp_project / "QMS" / "SOP" / "SOP-001-draft.md").exists()

    # Verify workspace copy created
    workspace_path = temp_project / ".claude" / "users" / "claude" / "workspace" / "SOP-001.md"
    assert workspace_path.exists(), "Workspace copy should be created"
