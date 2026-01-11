"""
QMS Verify Migration Command

Verifies migration completed successfully.

Created as part of CR-026: QMS CLI Extensibility Refactoring
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from registry import CommandRegistry
from qms_config import DOCUMENT_TYPES
from qms_paths import QMS_ROOT, get_doc_type
from qms_io import read_document
from qms_auth import get_current_user, verify_user_identity
from qms_meta import read_meta, get_meta_path


@CommandRegistry.register(
    name="verify-migration",
    help="Verify migration completed successfully",
)
def cmd_verify_migration(args) -> int:
    """Verify migration completed successfully."""
    user = get_current_user(args)

    if not verify_user_identity(user):
        return 1

    print("Verifying migration...")
    print("=" * 70)

    issues = []

    for doc_type, config in DOCUMENT_TYPES.items():
        doc_path = QMS_ROOT / config["path"]
        if not doc_path.exists():
            continue

        for md_file in doc_path.rglob("*.md"):
            if ".archive" in str(md_file):
                continue

            try:
                frontmatter, _ = read_document(md_file)
                doc_id = frontmatter.get("doc_id")

                if not doc_id:
                    continue

                actual_type = get_doc_type(doc_id)
                meta_path = get_meta_path(doc_id, actual_type)

                if not meta_path.exists():
                    issues.append(f"{doc_id}: Missing .meta file")
                else:
                    # Verify meta matches frontmatter
                    meta = read_meta(doc_id, actual_type)
                    if meta:
                        if meta.get("version") != frontmatter.get("version"):
                            issues.append(f"{doc_id}: Version mismatch (meta={meta.get('version')}, fm={frontmatter.get('version')})")
                        if meta.get("status") != frontmatter.get("status"):
                            issues.append(f"{doc_id}: Status mismatch (meta={meta.get('status')}, fm={frontmatter.get('status')})")

            except Exception as e:
                issues.append(f"{md_file}: Error - {e}")

    if issues:
        print("Issues found:")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    else:
        print("All documents verified successfully.")
        return 0
