"""
Interaction System — Compilation Engine

Compiles source data + template into markdown. Stateless transformation:
given source and template, produce the same output deterministically.

REQ-INT-016: Compilation

Created as part of CR-091: Interaction System Engine
"""

import re
from typing import Optional

from interact_source import (
    get_active_response, get_response_entries, get_loop_iteration,
    make_iteration_id,
)


def compile_document(source: dict, template_text: str) -> str:
    """
    Compile an interactive source into markdown.

    1. Strip all <!-- @... --> tags and guidance prose
    2. Keep markdown structure (headings, tables, code blocks)
    3. Substitute {{placeholders}} with active response values
    4. Render amendment trails (strikethrough on superseded entries)
    5. Show timestamps and author on all responses
    6. Show commit hashes on commit-enabled responses

    Args:
        source: The source data dict
        template_text: The raw template markdown

    Returns:
        Compiled markdown string
    """
    # Phase 1: Extract the template structure, stripping the header comment
    # and all guidance text between tags
    lines = template_text.split('\n')
    output_lines = []
    in_header_comment = False
    in_tag_comment = False
    skip_guidance = False
    tag_comment_buffer = []

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Detect start of HTML comment
        if '<!--' in stripped:
            comment_content = stripped

            # Check if comment closes on same line
            if '-->' in stripped:
                # Single-line comment — check if it's a tag
                match = re.search(r'<!--\s*@(\w[\w-]*)', comment_content)
                if match:
                    tag_name = match.group(1)
                    if tag_name == 'template':
                        # Skip entire header comment
                        i += 1
                        continue
                    # Skip tag comments and start skipping guidance
                    skip_guidance = True
                    i += 1
                    continue
                else:
                    # Non-tag comment (e.g., execution guidance) — keep it
                    output_lines.append(line)
                    i += 1
                    continue
            else:
                # Multi-line comment starts — check this line AND next line for tag
                match = re.search(r'<!--\s*@(\w[\w-]*)', comment_content)
                if not match and i + 1 < len(lines):
                    # Tag might be on the next line (e.g., <!--\n@template: ...)
                    next_stripped = lines[i + 1].strip()
                    if next_stripped.startswith('@'):
                        tag_match = re.match(r'@(\w[\w-]*)', next_stripped)
                        if tag_match:
                            match = tag_match
                if match:
                    in_tag_comment = True
                    tag_name = match.group(1)
                    if tag_name == 'template':
                        in_header_comment = True
                    i += 1
                    continue
                else:
                    # Non-tag multi-line comment — keep it
                    output_lines.append(line)
                    i += 1
                    continue

        # Inside header comment — skip until close
        if in_header_comment:
            if '-->' in stripped:
                in_header_comment = False
                in_tag_comment = False
                skip_guidance = True
            i += 1
            continue

        # Inside tag comment — skip until close
        if in_tag_comment:
            if '-->' in stripped:
                in_tag_comment = False
                skip_guidance = True
            i += 1
            continue

        # Skip guidance text between tags
        if skip_guidance:
            # Stop skipping at next structural element or placeholder
            if (stripped.startswith('#') or
                stripped.startswith('---') or
                stripped.startswith('|') or
                stripped.startswith('```') or
                re.search(r'\{\{.*\}\}', stripped)):
                skip_guidance = False
                # Fall through to process this line
            else:
                i += 1
                continue

        output_lines.append(line)
        i += 1

    # Phase 2: Substitute placeholders and render amendment trails
    result_lines = []
    for line in output_lines:
        # Find all {{placeholder}} patterns
        processed = _substitute_line(line, source)
        if processed is not None:
            result_lines.append(processed)

    # Phase 3: Expand loops
    result_text = '\n'.join(result_lines)
    result_text = _expand_loops(result_text, source)

    # Phase 4: Clean up excessive blank lines
    result_text = re.sub(r'\n{3,}', '\n\n', result_text)

    return result_text


def _substitute_line(line: str, source: dict) -> Optional[str]:
    """Substitute placeholders in a single line."""
    metadata = source.get("metadata", {})

    def replace_placeholder(m):
        ref_id = m.group(1)

        # Check metadata first
        if ref_id in metadata:
            return str(metadata[ref_id])

        # Check for special vars
        if ref_id == '_n':
            return ''  # Will be handled in loop expansion

        # Check responses
        entries = get_response_entries(source, ref_id)
        if entries:
            return _render_response(ref_id, entries)

        # Leave empty for unfilled
        return ''

    return re.sub(r'\{\{(\w+)\}\}', replace_placeholder, line)


def _render_response(prompt_id: str, entries: list) -> str:
    """Render a response value, including amendment trail if multiple entries."""
    if not entries:
        return ''

    if len(entries) == 1:
        # Single entry — just value with attribution
        entry = entries[0]
        attribution = _format_attribution(entry)
        return f"{entry['value']}\n{attribution}"

    # Multiple entries — amendment trail (REQ-INT-009)
    parts = []
    for i, entry in enumerate(entries):
        is_last = (i == len(entries) - 1)
        attribution = _format_attribution(entry)

        if is_last:
            # Active entry
            parts.append(f"{entry['value']}\n{attribution}")
        else:
            # Superseded entry — strikethrough
            reason = entry.get('reason', '')
            parts.append(f"~~{entry['value']}~~\n{attribution}")

    return '\n'.join(parts)


def _format_attribution(entry: dict) -> str:
    """Format an attribution line for a response entry."""
    author = entry.get('author', 'unknown')
    timestamp = entry.get('timestamp', '')
    # Simplify timestamp for display
    if 'T' in timestamp:
        timestamp = timestamp.split('T')[0] + ' ' + timestamp.split('T')[1].replace('Z', '')

    parts = [f"*-- {author}, {timestamp}"]

    if entry.get('commit'):
        parts.append(f" | commit: {entry['commit']}")

    if entry.get('reason'):
        parts.append(f" | Amended: {entry['reason']}")

    return ''.join(parts) + '*'


def _expand_loops(text: str, source: dict) -> str:
    """
    Expand loop iteration references in the compiled text.

    For prompts that are iteration-indexed (e.g., step_instructions),
    the template has a single placeholder {{step_instructions}} but the
    source has step_instructions.1, step_instructions.2, etc.

    This function detects the loop pattern and expands iterations.
    """
    # Find all iteration-indexed responses
    loop_prompts = {}  # base_id -> {iteration -> entries}
    for prompt_id, entries in source.get("responses", {}).items():
        if '.' in prompt_id:
            parts = prompt_id.rsplit('.', 1)
            if parts[1].isdigit():
                base = parts[0]
                iteration = int(parts[1])
                if base not in loop_prompts:
                    loop_prompts[base] = {}
                loop_prompts[base][iteration] = entries

    # For each loop in the source, check if we need to duplicate sections
    for loop_name, loop_data in source.get("loops", {}).items():
        iterations = loop_data.get("iterations", 0)
        if iterations < 1:
            continue

        # Find the step section pattern in the text and duplicate for iterations
        # Look for "### Step" followed by content until next "### Step" or "## "
        step_pattern = re.compile(
            r'(### Step\s*\n)(.*?)(?=### Step|\n## |\Z)',
            re.DOTALL
        )

        match = step_pattern.search(text)
        if match:
            # We have one step block that should be expanded to N iterations
            # But the responses are already iteration-indexed, so we need
            # to generate N blocks, each with its own iteration's data
            step_blocks = []
            for n in range(1, iterations + 1):
                block = f"### Step {n}\n\n"
                # Find all prompts in this loop and render their iteration values
                for base_id, iter_data in loop_prompts.items():
                    if n in iter_data:
                        entries = iter_data[n]
                        rendered = _render_response(f"{base_id}.{n}", entries)
                        # Add the rendered content with appropriate formatting
                        if base_id.startswith("step_instructions"):
                            block += f"**{rendered}**\n\n"
                        elif base_id.startswith("step_expected"):
                            block += f"**Expected:** {rendered}\n\n"
                        elif base_id.startswith("step_actual"):
                            block += f"**Actual:**\n\n```\n{rendered}\n```\n\n"
                        elif base_id.startswith("step_outcome"):
                            block += f"**Outcome:** {rendered}\n\n"

                step_blocks.append(block)

            # Replace the single step block with all expanded blocks
            expanded = '\n'.join(step_blocks)
            text = step_pattern.sub(expanded, text, count=1)

    return text


def compile_preview(source: dict, template_text: str) -> str:
    """
    Compile a preview (same as compile_document but labeled as preview).

    REQ-INT-013: --compile outputs to stdout for inspection.
    """
    return compile_document(source, template_text)
