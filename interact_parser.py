"""
Interaction System — Template Parser

Parses interactive templates into a state machine graph.
Templates embed tags in HTML comments that define prompts, gates, loops,
and transitions between them.

Tag vocabulary (REQ-INT-001):
    @template: name | version: N | start: id
    @prompt: id | next: id [| commit: true] [| default: value]
    @gate: id | type: yesno | yes: id | no: id
    @loop: name
    @end-loop: name
    @end

Created as part of CR-091: Interaction System Engine
"""

import re
from dataclasses import dataclass, field
from typing import Optional


# =============================================================================
# Node types in the template graph
# =============================================================================

@dataclass
class TemplateHeader:
    """Template metadata from @template tag (REQ-INT-002)."""
    name: str
    version: int
    start: str


@dataclass
class PromptNode:
    """A content prompt node (REQ-INT-003)."""
    id: str
    next: str
    commit: bool = False
    default: Optional[str] = None
    guidance: str = ""
    loop: Optional[str] = None
    iteration_indexed: bool = False


@dataclass
class GateNode:
    """A flow-control gate node (REQ-INT-004)."""
    id: str
    gate_type: str  # "yesno"
    yes: str
    no: str
    guidance: str = ""
    loop: Optional[str] = None
    iteration_indexed: bool = False


@dataclass
class LoopDef:
    """Loop definition from @loop/@end-loop pair (REQ-INT-005)."""
    name: str
    first_prompt: Optional[str] = None


@dataclass
class TemplateGraph:
    """The complete parsed template."""
    header: TemplateHeader
    nodes: dict = field(default_factory=dict)  # id -> PromptNode | GateNode
    loops: dict = field(default_factory=dict)  # name -> LoopDef
    raw_template: str = ""

    def get_node(self, node_id: str):
        """Get a node by ID, or None if not found."""
        return self.nodes.get(node_id)

    def get_prompt_ids(self) -> list:
        """Get all prompt node IDs in insertion order."""
        return [nid for nid, node in self.nodes.items()
                if isinstance(node, PromptNode)]

    def get_gate_ids(self) -> list:
        """Get all gate node IDs."""
        return [nid for nid, node in self.nodes.items()
                if isinstance(node, GateNode)]


# =============================================================================
# Parser
# =============================================================================

# Match HTML comment blocks: <!-- ... -->
_COMMENT_RE = re.compile(r'<!--\s*(.*?)\s*-->', re.DOTALL)

# Match individual tag lines within comments
_TAG_RE = re.compile(r'@(\w[\w-]*)\s*(?::\s*(.*))?$')


def _parse_attributes(attr_string: str) -> dict:
    """Parse pipe-delimited attributes: 'id | next: foo | commit: true'."""
    attrs = {}
    if not attr_string:
        return attrs

    parts = [p.strip() for p in attr_string.split('|')]
    for part in parts:
        if ':' in part:
            key, value = part.split(':', 1)
            key = key.strip()
            value = value.strip()
            # Type coercion
            if value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False
            elif value.isdigit():
                value = int(value)
            attrs[key] = value
        elif part:
            # Bare value is treated as 'id'
            if 'id' not in attrs:
                attrs['id'] = part
    return attrs


def _extract_guidance(template_text: str, tag_start_pos: int, next_tag_pos: int) -> str:
    """Extract guidance text between a tag and the next tag or placeholder."""
    segment = template_text[tag_start_pos:next_tag_pos]

    # Remove the opening comment tag itself
    segment = _COMMENT_RE.sub('', segment).strip()

    # The guidance is everything up to the placeholder line
    # Remove lines that are just {{...}} placeholders
    lines = segment.split('\n')
    guidance_lines = []
    for line in lines:
        stripped = line.strip()
        if re.match(r'^\*?\*?{{.*}}\*?\*?$', stripped):
            continue
        if stripped.startswith('```') and '{{' in stripped:
            continue
        if stripped == '```' and guidance_lines and '{{' in (guidance_lines[-1] if guidance_lines else ''):
            continue
        guidance_lines.append(line)

    return '\n'.join(guidance_lines).strip()


def parse_template(template_text: str) -> TemplateGraph:
    """
    Parse an interactive template into a TemplateGraph.

    Args:
        template_text: Raw template markdown with embedded tags

    Returns:
        TemplateGraph with all nodes, loops, and header

    Raises:
        ValueError: If template is malformed
    """
    header = None
    nodes = {}
    loops = {}
    current_loop = None

    # Find all comment blocks and their positions
    # Tags may be in single-line comments (<!-- @prompt: ... -->)
    # or the first line of multi-line comments (<!-- @template: ... \n ... -->)
    tag_positions = []
    for match in _COMMENT_RE.finditer(template_text):
        comment_body = match.group(1).strip()
        # Check first line of comment for a tag
        first_line = comment_body.split('\n')[0].strip()
        tag_match = _TAG_RE.match(first_line)
        if tag_match:
            tag_name = tag_match.group(1)
            tag_rest = tag_match.group(2) or ""
            tag_positions.append({
                'tag': tag_name,
                'attrs_raw': tag_rest,
                'start': match.start(),
                'end': match.end(),
            })

    if not tag_positions:
        raise ValueError("No interactive tags found in template")

    # Process tags
    for i, tp in enumerate(tag_positions):
        tag = tp['tag']
        attrs = _parse_attributes(tp['attrs_raw'])

        if tag == 'template':
            # REQ-INT-002: Template header
            name = attrs.get('id') or attrs.get('name', '')
            version = attrs.get('version', 1)
            start = attrs.get('start', '')
            if not name:
                raise ValueError("@template tag missing name")
            if not start:
                raise ValueError("@template tag missing start prompt")
            header = TemplateHeader(name=str(name), version=int(version), start=str(start))

        elif tag == 'prompt':
            # REQ-INT-003: Prompt node
            prompt_id = attrs.get('id', '')
            if not prompt_id:
                raise ValueError("@prompt tag missing id")
            next_id = attrs.get('next', '')
            if not next_id:
                raise ValueError(f"@prompt '{prompt_id}' missing next")

            # Extract guidance text between this tag and the next
            next_pos = tag_positions[i + 1]['start'] if i + 1 < len(tag_positions) else len(template_text)
            guidance = _extract_guidance(template_text, tp['end'], next_pos)

            node = PromptNode(
                id=str(prompt_id),
                next=str(next_id),
                commit=bool(attrs.get('commit', False)),
                default=attrs.get('default'),
                guidance=guidance,
                loop=current_loop,
                iteration_indexed=current_loop is not None,
            )
            nodes[node.id] = node

            # Track first prompt in a loop
            if current_loop and loops[current_loop].first_prompt is None:
                loops[current_loop].first_prompt = node.id

        elif tag == 'gate':
            # REQ-INT-004: Gate node
            gate_id = attrs.get('id', '')
            if not gate_id:
                raise ValueError("@gate tag missing id")
            gate_type = attrs.get('type', 'yesno')
            yes_target = attrs.get('yes', '')
            no_target = attrs.get('no', '')
            if not yes_target or not no_target:
                raise ValueError(f"@gate '{gate_id}' missing yes/no targets")

            # Extract guidance
            next_pos = tag_positions[i + 1]['start'] if i + 1 < len(tag_positions) else len(template_text)
            guidance = _extract_guidance(template_text, tp['end'], next_pos)

            node = GateNode(
                id=str(gate_id),
                gate_type=str(gate_type),
                yes=str(yes_target),
                no=str(no_target),
                guidance=guidance,
                loop=current_loop,
                iteration_indexed=current_loop is not None,
            )
            nodes[node.id] = node

        elif tag == 'loop':
            # REQ-INT-005: Loop start
            loop_name = attrs.get('id') or tp['attrs_raw'].strip()
            if not loop_name:
                raise ValueError("@loop tag missing name")
            current_loop = str(loop_name)
            loops[current_loop] = LoopDef(name=current_loop)

        elif tag == 'end-loop':
            # REQ-INT-005: Loop end
            loop_name = attrs.get('id') or tp['attrs_raw'].strip()
            if str(loop_name) != current_loop:
                raise ValueError(f"@end-loop '{loop_name}' does not match open @loop '{current_loop}'")
            current_loop = None

        elif tag == 'end':
            # Terminal state — represented by a sentinel in the graph
            nodes['__end__'] = PromptNode(id='__end__', next='')

    if header is None:
        raise ValueError("Template missing @template header")

    if current_loop is not None:
        raise ValueError(f"Unclosed loop: {current_loop}")

    return TemplateGraph(
        header=header,
        nodes=nodes,
        loops=loops,
        raw_template=template_text,
    )
