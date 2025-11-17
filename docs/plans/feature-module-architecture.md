# Feature-Based Module Architecture Plan

## Overview

Refactor the codebase from a monolithic `commands.py` (2795 lines) to a feature-based module architecture where each feature is self-contained with its own CLI, models, commands, and utilities.

## Goals

- **Scalability**: Easy to add new features without creating mega-files
- **Self-contained**: Each feature owns its domain logic
- **Clear boundaries**: Easy to find and modify feature-specific code
- **Maintainability**: Smaller, focused modules instead of large files
- **Testability**: Each feature can be tested in isolation
- **Pluggability**: Features register themselves with the main CLI

## Current Problems

- `commands.py`: 2795 lines (mega-file)
- Repeated patterns across commands (storage loading, validation, gates)
- Hard to navigate and find specific functionality
- Adding new features means editing massive files
- No clear separation between feature domains

## Proposed Architecture

```
src/taskpy/
├── core/                    # Core task management
│   ├── __init__.py
│   ├── cli.py              # create, edit, show, list, rename, delete, recover
│   ├── models.py           # Task, TaskStatus models
│   ├── commands.py         # Core command implementations
│   └── utils.py            # Core-specific utilities
│
├── workflow/               # Workflow & status management
│   ├── __init__.py
│   ├── cli.py              # promote, demote, move
│   ├── gates.py            # Gate validation logic
│   ├── commands.py         # Workflow command implementations
│   └── models.py           # Workflow-specific models if needed
│
├── sprint/                 # Sprint management
│   ├── __init__.py
│   ├── cli.py              # sprint add/remove/list/stats/recommend
│   ├── models.py           # Sprint model
│   ├── commands.py         # Sprint command implementations
│   ├── intelligence.py     # Sprint recommendations (existing)
│   └── utils.py            # Sprint-specific utilities
│
├── epics/                  # Epic management
│   ├── __init__.py
│   ├── cli.py              # epics list/add/delete/enable/disable
│   ├── models.py           # Epic model
│   ├── commands.py         # Epic command implementations
│   └── recommendations.py  # Epic keyword matching (FEAT-46)
│
├── milestones/            # Milestone management
│   ├── __init__.py
│   ├── cli.py              # milestones, milestone commands
│   ├── models.py           # Milestone model
│   └── commands.py         # Milestone command implementations
│
├── nfrs/                   # NFR management
│   ├── __init__.py
│   ├── cli.py              # nfrs commands
│   ├── models.py           # NFR model
│   └── commands.py         # NFR command implementations
│
├── linking/                # Task relationships (FEAT-05)
│   ├── __init__.py
│   ├── cli.py              # link, unlink commands
│   ├── models.py           # Relationship models
│   ├── commands.py         # Link command implementations
│   └── utils.py            # Relationship traversal utilities
│
├── splitting/              # Task splitting (FEAT-08)
│   ├── __init__.py
│   ├── cli.py              # split command
│   ├── models.py           # Split-specific models
│   ├── commands.py         # Split command implementation
│   └── utils.py            # Child creation, renumbering logic
│
├── admin/                  # Admin & maintenance
│   ├── __init__.py
│   ├── cli.py              # init, groom, manifest, verify, session
│   ├── commands.py         # Admin command implementations
│   └── utils.py            # Admin utilities
│
├── display/                # Display & visualization
│   ├── __init__.py
│   ├── cli.py              # info, stoplight, kanban, stats, history
│   ├── commands.py         # Display command implementations
│   └── formatters.py       # Output formatting (boxy/rolo)
│
├── blocking/               # Task blocking/dependencies
│   ├── __init__.py
│   ├── cli.py              # block, unblock commands
│   ├── models.py           # Blocker models
│   └── commands.py         # Blocking command implementations
│
├── storage/                # Storage layer
│   ├── __init__.py
│   ├── storage.py          # Storage class (current storage.py)
│   └── loader.py           # Task loading utilities
│
├── shared/                 # Shared utilities across features
│   ├── __init__.py
│   ├── aggregations.py     # Aggregation utilities (REF-05)
│   ├── validation.py       # Input validation
│   └── history.py          # History utilities (QOL-15)
│
├── cli.py                  # Main CLI entry point (registers all feature CLIs)
├── models.py               # Re-exports all models for backward compat
└── output.py               # Keep existing output utilities
```

## Feature Module Pattern

Each feature module follows a consistent pattern:

### Directory Structure
```
feature_name/
├── __init__.py          # Expose public API
├── cli.py               # CLI registration and argument parsing
├── models.py            # Feature-specific data models
├── commands.py          # Command implementation functions
└── utils.py             # Feature-specific utilities (optional)
```

### CLI Registration Pattern

**Feature module CLI (e.g., `epics/cli.py`):**
```python
"""Epic management CLI registration."""
import argparse
from .commands import cmd_epics

def register():
    """
    Register epic commands with main CLI.

    Returns:
        dict: Command registration config
    """
    return {
        'epics': {
            'func': cmd_epics,
            'help': 'Manage epics',
            'parser': setup_parser
        }
    }

def setup_parser(parser: argparse.ArgumentParser):
    """
    Configure epics command parser.

    Args:
        parser: Subparser for epics command
    """
    # Global flags are already added by main CLI
    # Add feature-specific flags here
    parser.add_argument('--add', metavar='NAME', help='Add a new epic')
    parser.add_argument('--delete', metavar='NAME', help='Delete or disable epic')
    parser.add_argument('--enable', metavar='NAME', help='Enable epic')
    parser.add_argument('--disable', metavar='NAME', help='Disable epic')

__all__ = ['register']
```

### Main CLI Registration

**Main CLI (`cli.py`):**
```python
"""Main CLI entry point with feature registration."""
import argparse
from taskpy import (
    core, workflow, sprint, epics, milestones,
    nfrs, linking, splitting, admin, display, blocking
)

# Global flags that apply to all commands
GLOBAL_FLAGS = [
    ('--view', {'choices': ['pretty', 'data'], 'help': 'Output mode'}),
    ('--data', {'action': 'store_true', 'help': 'Plain data output'}),
    ('--no-boxy', {'action': 'store_true', 'help': 'Disable boxy output'}),
    ('--agent', {'action': 'store_true', 'help': 'Agent-friendly output'}),
    ('-v', '--version', {'action': 'store_true', 'help': 'Show version'}),
]

def add_global_flags(parser: argparse.ArgumentParser):
    """Add global flags to a parser."""
    for flag_names, kwargs in GLOBAL_FLAGS:
        if isinstance(flag_names, tuple):
            parser.add_argument(*flag_names, **kwargs)
        else:
            parser.add_argument(flag_names, **kwargs)

def build_cli():
    """Build CLI with all registered features."""
    parser = argparse.ArgumentParser(
        prog='taskpy',
        description='File-based agile task management'
    )

    # Add global flags to main parser
    add_global_flags(parser)

    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Register all features
    features = [
        core, workflow, sprint, epics, milestones,
        nfrs, linking, splitting, admin, display, blocking
    ]

    for feature in features:
        commands = feature.cli.register()

        for cmd_name, cmd_config in commands.items():
            # Create subparser for this command
            cmd_parser = subparsers.add_parser(
                cmd_name,
                help=cmd_config['help']
            )

            # Add global flags to subparser
            add_global_flags(cmd_parser)

            # Let feature configure its own parser (feature-specific flags)
            cmd_config['parser'](cmd_parser)

            # Set command function
            cmd_parser.set_defaults(func=cmd_config['func'])

    return parser

def main():
    """Main entry point."""
    parser = build_cli()
    args = parser.parse_args()

    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
```

## Flag System Architecture

### Global Flags

Global flags are available on ALL commands and subcommands:
- `--view {pretty,data}` - Output mode
- `--data` - Plain data output (shorthand for --view=data)
- `--no-boxy` - Disable boxy output
- `--agent` - Agent-friendly output
- `-v, --version` - Show version
- `--all` - Show all items including done/archived
- `--mode {TEST,DEV,PROD}` - Runtime mode (FEAT-42)

**Implementation:**
- Global flags added to main parser
- Global flags also added to each subparser
- Ensures flags work at any command level

**Examples:**
```bash
taskpy --data list              # Global flag before command
taskpy list --data              # Global flag after command
taskpy sprint add FEAT-01 --data  # Global flag on subcommand
```

### Feature-Specific Flags

Feature modules can add their own flags specific to their domain:

**Example: Epic module flags**
```python
# epics/cli.py
def setup_parser(parser):
    parser.add_argument('--add', metavar='NAME', help='Add epic')
    parser.add_argument('--delete', metavar='NAME', help='Delete epic')
    # ... etc
```

**Example: Split module flags**
```python
# splitting/cli.py
def setup_parser(parser):
    parser.add_argument('task_id', help='Task to split')
    parser.add_argument('--epic', metavar='EPIC', help='New epic for split tasks')
    parser.add_argument('--count', type=int, help='Number of children')
    parser.add_argument('--child', action='append', help='Explicit child title')
    parser.add_argument('--dry-run', action='store_true', help='Preview only')
```

### Flag Precedence & Parsing

1. **Argparse handles precedence automatically**: Last occurrence wins
2. **Global flags accessible in all commands**: `args.data`, `args.view`, etc.
3. **Feature flags only accessible in their commands**: `args.add` only in epics

### Testing Flag Behavior

**Global flag test:**
```python
def test_global_flag_on_any_command():
    """Global flags work on all commands."""
    assert parse_args(['list', '--data']).data == True
    assert parse_args(['--data', 'list']).data == True
    assert parse_args(['sprint', 'add', 'FEAT-01', '--data']).data == True
```

**Feature flag test:**
```python
def test_feature_specific_flags():
    """Feature flags only work on their commands."""
    args = parse_args(['epics', '--add', 'NEWEPIC'])
    assert args.add == 'NEWEPIC'

    # Should error on non-epic commands
    with pytest.raises(SystemExit):
        parse_args(['list', '--add', 'NEWEPIC'])
```

## Model Organization

### Core Models (models.py)
Re-export all models for backward compatibility:
```python
"""Backward compatibility: re-export all models."""
from .core.models import Task, TaskStatus, Priority
from .epics.models import Epic
from .sprint.models import Sprint
from .milestones.models import Milestone
from .nfrs.models import NFR
from .linking.models import Relationship, RelationshipType

__all__ = [
    'Task', 'TaskStatus', 'Priority',
    'Epic', 'Sprint', 'Milestone', 'NFR',
    'Relationship', 'RelationshipType'
]
```

### Feature-Specific Models
Each feature defines its own models:
```python
# epics/models.py
@dataclass
class Epic:
    name: str
    description: str
    active: bool = True
    epic_type: str = "project"  # "standard" or "project"
    keywords: List[str] = field(default_factory=list)
    story_point_budget: Optional[int] = None
```

## Shared Utilities (shared/ module)

Common utilities used across features:

### Aggregations (REF-05)
```python
# shared/aggregations.py
def count_tasks_by_status(tasks, status):
    """Count tasks in a specific status."""
    return len([t for t in tasks if t.status == status])

def sum_story_points(tasks):
    """Sum story points across tasks."""
    return sum(t.story_points or 0 for t in tasks)

def filter_by_sprint(tasks, in_sprint=True):
    """Filter tasks by sprint membership."""
    return [t for t in tasks if t.in_sprint == in_sprint]
```

### History (QOL-15)
```python
# shared/history.py
def add_history_entry(task, action, **kwargs):
    """Add history entry to task."""
    entry = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'action': action,
        **kwargs
    }
    if not hasattr(task, 'history') or task.history is None:
        task.history = []
    task.history.append(entry)
    task.updated = datetime.now(timezone.utc)
```

### Validation
```python
# shared/validation.py
def validate_task_id(task_id):
    """Validate task ID format."""
    pattern = r'^[A-Z]{2,4}-\d+[a-z]?$'
    return re.match(pattern, task_id) is not None

def parse_task_id(task_id):
    """Parse task ID into epic and number."""
    match = re.match(r'^([A-Z]{2,4})-(\d+)([a-z]?)$', task_id)
    if not match:
        raise ValueError(f"Invalid task ID: {task_id}")
    return match.group(1), match.group(2) + match.group(3)
```

## Migration Strategy

### Phase 1: Create Feature Module Structure
1. Create all feature directories
2. Create empty `__init__.py`, `cli.py`, `models.py`, `commands.py` files
3. Set up registration pattern in each `cli.py`

### Phase 2: Extract Shared Utilities
1. Create `shared/` module
2. Extract aggregation logic (REF-05)
3. Extract history utilities (QOL-15)
4. Extract validation utilities
5. Test utilities in isolation

### Phase 3: Migrate Features Incrementally
Start with smallest/simplest features first:

1. **NFRs module** (smallest, simplest)
   - Move `cmd_nfrs()` → `nfrs/commands.py`
   - Create `nfrs/cli.py` registration
   - Test NFRs command works

2. **Epics module**
   - Move `cmd_epics()` → `epics/commands.py`
   - Move `Epic` model → `epics/models.py`
   - Create `epics/cli.py` registration
   - Test epics command works

3. **Milestones module**
   - Move milestone commands → `milestones/`
   - Move Milestone model
   - Test milestone commands

4. **Sprint module**
   - Move sprint commands → `sprint/`
   - Move Sprint model and intelligence.py
   - Test sprint commands

5. **Continue with larger features...**

### Phase 4: Update Main CLI
1. Update `cli.py` to use registration system
2. Add global flag handling
3. Test all commands still work
4. Verify backward compatibility

### Phase 5: Cleanup
1. Remove old `commands.py`
2. Update imports throughout codebase
3. Update tests to use new structure
4. Update documentation

## Backward Compatibility

### Import Compatibility
Old imports continue to work:
```python
# Old style (still works)
from taskpy.commands import cmd_create
from taskpy.models import Task, Epic

# New style (preferred)
from taskpy.core.commands import cmd_create
from taskpy.core.models import Task
from taskpy.epics.models import Epic
```

### CLI Compatibility
All existing CLI commands continue to work exactly the same:
```bash
# Everything still works
taskpy create FEAT "New feature" --sp 5
taskpy list --status backlog
taskpy sprint add FEAT-01
taskpy epics --add NEWEPIC
```

## Benefits

1. **Scalability**: New features = new module, no mega-files
2. **Maintainability**: Easy to find and modify feature code
3. **Testability**: Test features in isolation
4. **Clear ownership**: Each feature owns its domain
5. **Independent development**: Features don't interfere with each other
6. **Pluggable architecture**: Features can be enabled/disabled
7. **Consistent patterns**: All features follow same structure
8. **Self-documenting**: Structure shows what features exist

## Example: Adding a New Feature

To add ticket types feature (FEAT-44):

1. Create `src/taskpy/ticket_types/` module
2. Create files:
   ```
   ticket_types/
   ├── __init__.py
   ├── cli.py              # Register 'types' command
   ├── models.py           # TicketType model
   ├── commands.py         # cmd_types() implementation
   └── recommendations.py  # Type recommendation logic
   ```
3. Implement registration in `cli.py`:
   ```python
   def register():
       return {
           'types': {
               'func': cmd_types,
               'help': 'List and manage ticket types',
               'parser': setup_parser
           }
       }
   ```
4. Add to main CLI feature list in `cli.py`
5. Done! Feature is integrated and isolated

## Open Questions

- [ ] How to handle cross-feature dependencies? (e.g., sprint needs core.models.Task)
  - Answer: Import from feature modules directly, or use shared models in core

- [ ] Should storage be a feature or stay separate?
  - Leaning toward: Keep separate as infrastructure layer

- [ ] How to handle output formatting across features?
  - Answer: Keep output.py separate, features import from it

- [ ] Migration order for large features like core?
  - Answer: Do last, after pattern is proven with smaller features

## Related Tasks

- REF-04: Break up mega files and extract shared utilities
- REF-05: Create shared aggregation utility module
- FEAT-05: Implement subtask linking and hierarchy
- FEAT-08: Implement taskpy split
- FEAT-46: Add epic management commands
- QOL-15: Add history logging for all task-modifying commands
