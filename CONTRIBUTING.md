# Contributing to QMS CLI

This guide covers the internal architecture of the QMS CLI for developers adding features or fixing bugs.

## Architecture Overview

```
qms-cli/
├── qms.py              # Entry point, argparse definitions
├── registry.py         # CommandRegistry - command dispatch
├── workflow.py         # WorkflowEngine - state machine logic
├── prompts.py          # PromptRegistry - task prompt generation
├── context.py          # CommandContext - command helper utilities
├── qms_commands.py     # Re-export layer (backward compatibility)
├── qms_meta.py         # Metadata operations
├── qms_audit.py        # Audit trail operations
├── qms_paths.py        # Path constants
├── qms_templates.py    # Document templates
├── commands/           # Individual command implementations
│   ├── __init__.py
│   ├── create.py
│   ├── status.py
│   └── ...
└── tests/
    ├── test_imports.py
    ├── test_workflow.py
    ├── test_prompts.py
    ├── test_registry.py
    └── ...
```

## Adding a New Command

1. Create a new file in `commands/`:

```python
# commands/mycommand.py
from registry import CommandRegistry, CommandSpec, ArgumentSpec
from context import CommandContext

@CommandRegistry.register(
    CommandSpec(
        name="mycommand",
        help="Brief description of the command",
        arguments=[
            ArgumentSpec("doc_id", help="Document ID"),
            ArgumentSpec("--flag", action="store_true", help="Optional flag"),
        ]
    )
)
def cmd_mycommand(args) -> int:
    """Execute mycommand."""
    ctx = CommandContext.from_args(args)

    # Use ctx helpers for validation
    ctx.require_document_exists()
    ctx.require_permission("mycommand")

    # Implementation here...

    ctx.print_success("Operation completed")
    return 0
```

2. Import it in `commands/__init__.py`:

```python
from commands import mycommand
```

3. Add argparse definition in `qms.py` (in the subparsers section):

```python
p = subparsers.add_parser("mycommand", help="Brief description")
p.add_argument("doc_id", help="Document ID")
p.add_argument("--flag", action="store_true", help="Optional flag")
```

4. Add tests in `tests/`.

## Modifying Workflow Transitions

All state machine logic is centralized in `workflow.py`.

### Adding a New Transition

Edit `WORKFLOW_TRANSITIONS` in `WorkflowEngine`:

```python
WORKFLOW_TRANSITIONS: List[StatusTransition] = [
    # Existing transitions...

    StatusTransition(
        from_status="NEW_STATUS",
        to_status="TARGET_STATUS",
        action=Action.MY_ACTION,
        workflow_type=WorkflowType.EXECUTABLE,
        execution_phase=ExecutionPhase.PRE,
    ),
]
```

### Using the WorkflowEngine

```python
from workflow import WorkflowEngine, Action

engine = WorkflowEngine()

# Get valid transition
transition = engine.get_transition(
    current_status="DRAFT",
    action=Action.ROUTE_REVIEW,
    is_executable=True
)
# Returns StatusTransition or None

# Check status categories
engine.is_review_status("IN_REVIEW")      # True
engine.is_approval_status("IN_APPROVAL")  # True

# Get target statuses
engine.get_reviewed_status("IN_REVIEW")           # "REVIEWED"
engine.get_approved_status("IN_APPROVAL", False)  # "EFFECTIVE"
engine.get_rejection_target("IN_APPROVAL")        # "REVIEWED"
```

## Customizing Prompts

Task prompts are managed by `PromptRegistry` in `prompts.py`.

### Registering Custom Prompts

```python
from prompts import PromptRegistry, PromptConfig, ChecklistItem

PromptRegistry.register(
    doc_type="MY_TYPE",
    workflow_type="review",  # or "approval"
    config=PromptConfig(
        preamble="Review this document for...",
        checklist=[
            ChecklistItem(
                category="Technical",
                items=["Verify X", "Check Y"]
            ),
        ],
        closing="Submit review with --recommend or --request-updates."
    )
)
```

### Using the PromptRegistry

```python
from prompts import PromptRegistry

# Generate prompt text
prompt = PromptRegistry.generate(
    doc_type="CR",
    workflow_type="review",
    phase="pre"  # or "post"
)
```

## CommandContext

`CommandContext` eliminates boilerplate in command implementations.

### Creating Context

```python
from context import CommandContext

ctx = CommandContext.from_args(args)
```

### Validation Methods

```python
ctx.require_document_exists()      # Raises if doc doesn't exist
ctx.require_checked_out()          # Raises if not checked out
ctx.require_not_checked_out()      # Raises if checked out
ctx.require_permission("command")  # Raises if user lacks permission
ctx.require_responsible_user()     # Raises if user isn't responsible
ctx.require_status("DRAFT")        # Raises if status doesn't match
ctx.require_assignee()             # Raises if user not assigned
```

### Convenience Properties

```python
ctx.doc_id          # Document ID from args
ctx.user            # Username from args
ctx.meta            # Loaded metadata dict
ctx.content         # Document content (lazy-loaded)
ctx.is_executable   # Whether doc type is executable
ctx.status          # Current document status
```

### Output Methods

```python
ctx.print_success("Done!")
ctx.print_error("Failed!")
ctx.print_warning("Caution...")
ctx.print_info("FYI...")
```

## Testing

### Running Tests

```bash
# All tests
python -m pytest qms-cli/tests/ -v

# Specific test file
python -m pytest qms-cli/tests/test_workflow.py -v

# Specific test
python -m pytest qms-cli/tests/test_workflow.py::test_route_review_transition -v
```

### Test Categories

| File | Purpose |
|------|---------|
| `test_imports.py` | Verify all modules import correctly, no circular deps |
| `test_workflow.py` | WorkflowEngine transitions and helpers |
| `test_prompts.py` | PromptRegistry generation and configs |
| `test_registry.py` | CommandRegistry registration and dispatch |
| `test_qms.py` | Integration tests for CLI commands |

### Writing Tests

```python
# tests/test_myfeature.py
import pytest

def test_my_feature():
    """Test description."""
    # Arrange
    # Act
    # Assert
    pass

@pytest.mark.parametrize("input,expected", [
    ("a", 1),
    ("b", 2),
])
def test_parametrized(input, expected):
    """Test multiple cases."""
    assert process(input) == expected
```

## Code Style

- Keep command files under 200 lines
- Use `CommandContext` for common operations
- Use `WorkflowEngine` for state transitions (no hardcoded status checks)
- Use `PromptRegistry` for task prompts
- All new code requires tests

## File Size Guidelines

| Component | Target | Max |
|-----------|--------|-----|
| Command file | < 100 lines | 200 lines |
| Infrastructure module | < 400 lines | 500 lines |
| Test file | < 200 lines | 300 lines |

If a file exceeds these limits, consider decomposition.
