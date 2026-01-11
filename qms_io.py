"""
QMS CLI Document I/O Module

Contains functions for reading and writing QMS documents,
including frontmatter parsing and serialization.
"""
from pathlib import Path
from typing import Dict, Any
import yaml

from qms_config import AUTHOR_FRONTMATTER_FIELDS


# =============================================================================
# Frontmatter Parsing
# =============================================================================

def parse_frontmatter(content: str) -> tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    try:
        frontmatter = yaml.safe_load(parts[1])
        body = parts[2].lstrip("\n")
        return frontmatter or {}, body
    except yaml.YAMLError:
        return {}, content


def serialize_frontmatter(frontmatter: Dict[str, Any], body: str) -> str:
    """Serialize frontmatter and body back to markdown."""
    yaml_str = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return f"---\n{yaml_str}---\n\n{body}"


# =============================================================================
# Document I/O
# =============================================================================

def read_document(path: Path) -> tuple[Dict[str, Any], str]:
    """Read a document and parse its frontmatter."""
    if not path.exists():
        raise FileNotFoundError(f"Document not found: {path}")
    content = path.read_text(encoding="utf-8")
    return parse_frontmatter(content)


def write_document(path: Path, frontmatter: Dict[str, Any], body: str):
    """Write a document with frontmatter."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = serialize_frontmatter(frontmatter, body)
    path.write_text(content, encoding="utf-8")


# =============================================================================
# Frontmatter Filtering
# =============================================================================

def filter_author_frontmatter(frontmatter: Dict[str, Any]) -> Dict[str, Any]:
    """Extract only author-maintained fields from frontmatter."""
    return {k: v for k, v in frontmatter.items() if k in AUTHOR_FRONTMATTER_FIELDS}


def write_document_minimal(path: Path, frontmatter: Dict[str, Any], body: str):
    """Write a document with minimal (author-maintained only) frontmatter."""
    minimal_fm = filter_author_frontmatter(frontmatter)
    write_document(path, minimal_fm, body)
