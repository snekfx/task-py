# TaskPy - META PROCESS v4 Task Management

File-based agile task management tool designed for META PROCESS v4 workflows. Lightweight, git-friendly, and perfect for both AI agents and human developers.

## What is META PROCESS v4?

META PROCESS v4 is an evolution of v3 that addresses key inefficiencies through **automation and structured data**:

### Problems with v3:
- Manual HANDOFF.md updates (often forgotten)
- Manual TASKS.txt hygiene (completed items left behind)
- No structured task tracking (free-form text)
- Difficult to query task status programmatically
- No automatic session tracking
- Agents have to manually parse and update docs

### META PROCESS v4 Solutions:
- **Automated task lifecycle** via `taskpy` CLI
- **Structured task files** (Markdown + YAML frontmatter)
- **Fast queries** via TSV manifest
- **Kanban workflow** with file-based state
- **Automatic session logging** (coming soon)
- **Test verification hooks** for quality gates
- **Reference linking** (code, docs, plans, NFRs)

## Features

- ✅ **Epic-based organization** (BUGS-NN, DOCS-NN, FEAT-NN, etc.)
- ✅ **Kanban workflow** (stub → backlog → ready → in_progress → qa → done)
- ✅ **Milestone management** (organize multi-phase work with priority ordering)
- ✅ **Story point tracking** with milestone progress
- ✅ **Priority management** (critical, high, medium, low)
- ✅ **NFR compliance** (link Non-Functional Requirements to tasks)
- ✅ **Reference linking** (code files, docs, test files, plans)
- ✅ **Test verification** (integrate with pytest/cargo test)
- ✅ **Pretty output** via boxy/rolo or plain data mode
- ✅ **Git-friendly** (plain text, human-readable)
- ✅ **Fast queries** via TSV manifest
- ✅ **Extensible** (TOML configuration for epics, NFRs, and milestones)

## Installation

```bash
# Recommended: Use deploy script
cd task-py
./bin/deploy.sh

# Or install manually with pip
pip install -e .

# Or install from repo
pip install git+https://github.com/snekfx/task-py

# Development: Use bin wrapper (no install)
./bin/taskpy --version
```

## Quick Start

```bash
# Initialize TaskPy in your project
taskpy init

# Create a task (starts in stub status)
taskpy create FEAT "Add user authentication" --sp 5 --priority high

# Create task with milestone assignment
taskpy create FEAT "OAuth integration" --sp 8 --milestone milestone-1

# List tasks
taskpy list
taskpy list --milestone milestone-1    # Filter by milestone
taskpy list --status backlog            # Filter by status

# Show task details
taskpy show FEAT-01

# Edit task (opens in $EDITOR)
taskpy edit FEAT-01

# Move task through workflow
taskpy promote FEAT-01               # stub → backlog
taskpy promote FEAT-01               # backlog → ready
taskpy promote FEAT-01               # ready → in_progress
taskpy move FEAT-01 qa               # Move to specific status

# Milestone management
taskpy milestones                    # List all milestones
taskpy milestone show milestone-1    # Show milestone progress
taskpy milestone assign FEAT-01 milestone-1
taskpy milestone start milestone-2
taskpy milestone complete milestone-1

# View kanban board
taskpy kanban
taskpy kanban --epic FEAT

# Link references
taskpy link FEAT-01 --code src/auth.py --test tests/test_auth.py

# Run verification
taskpy verify FEAT-01

# Show statistics
taskpy stats
taskpy stats --epic FEAT
taskpy stats --milestone milestone-1

# Rebuild manifest index (resync existing task files)
taskpy manifest rebuild
```

## Directory Structure

```
your-project/
├── data/kanban/              # TaskPy data (gitignored by default)
│   ├── info/                 # Configuration files (tracked in git)
│   │   ├── epics.toml        # Epic definitions
│   │   ├── nfrs.toml         # NFR definitions
│   │   ├── milestones.toml   # Milestone definitions
│   │   └── config.toml       # TaskPy config
│   ├── status/               # Task files organized by status
│   │   ├── stub/             # Incomplete tasks (default)
│   │   ├── backlog/          # Ready for work
│   │   ├── ready/            # Prioritized for next sprint
│   │   ├── in_progress/      # Actively being worked on
│   │   ├── qa/               # In testing/review
│   │   ├── done/             # Completed
│   │   ├── archived/         # Long-term storage
│   │   └── blocked/          # Blocked by dependencies
│   ├── manifest.tsv          # Fast query index
│   └── references/
│       └── PLAN-*.md         # Strategic planning docs
├── docs/
│   ├── procs/                # META PROCESS v3 compatibility
│   │   ├── PROCESS.txt
│   │   ├── HANDOFF.md        # Auto-generated from sessions
│   │   └── QUICK_REF.txt     # Auto-generated summary
│   └── dev/
│       └── MODULE_SPEC.md
└── .gitignore                # Updated to exclude task data, track config
```

## Task File Format

Tasks are stored as Markdown files with YAML frontmatter:

```markdown
---
id: FEAT-01
title: Add user authentication
epic: FEAT
number: 1
status: in_progress
story_points: 5
priority: high
created: 2025-11-15T12:00:00
updated: 2025-11-15T14:30:00
assigned: session-001
milestone: milestone-1
blocked_reason: null
tags: [security, auth]
dependencies: []
blocks: [FEAT-02]
nfrs: [NFR-SEC-001, NFR-TEST-001]
references.code: [src/auth.py, src/user.py]
references.tests: [tests/test_auth.py]
verification.command: pytest tests/test_auth.py
verification.status: pending
---

# Add user authentication

## Description

Implement secure user authentication using JWT tokens with password hashing.

## Acceptance Criteria

- [ ] Password hashing with bcrypt
- [ ] JWT token generation and validation
- [ ] Login endpoint
- [ ] Logout endpoint
- [ ] Token refresh mechanism
- [ ] All tests passing

## Implementation Notes

Using the `jsonwebtoken` crate for JWT handling and `bcrypt` for password hashing.

## Security Considerations

- Never log passwords or tokens
- Use secure random for token secrets
- Implement rate limiting on login endpoint
```

## Epic Configuration

Customize your epics in `data/kanban/info/epics.toml`:

```toml
[BUGS]
description = "Bug fixes and corrections"
active = true

[FEAT]
description = "New features and enhancements"
active = true

[REF]
description = "Refactoring and code cleanup"
active = true

[RX]
description = "Research and exploration"
prefix = "RX"  # Custom prefix
active = true

[MYEPIC]
description = "Custom epic for your project"
active = true
story_point_budget = 100  # Optional SP limit
```

## Milestone Management

Define project milestones in `data/kanban/info/milestones.toml`:

```toml
[milestone-1]
name = "Foundation MVP"
description = "Core functionality and basic workflow"
priority = 1
status = "active"
goal_sp = 50

[milestone-2]
name = "Feature Complete"
description = "All planned features implemented"
priority = 2
status = "planned"
goal_sp = 100

[milestone-3]
name = "Polish and Release"
description = "UX improvements, documentation, and release prep"
priority = 3
status = "planned"
goal_sp = 40

# Milestones use semantic versioning for IDs
[milestone-1.5]
name = "Security Hardening"
description = "Address security audit findings"
priority = 2  # Injected between milestone-1 and milestone-2
status = "planned"
goal_sp = 20
```

### Milestone Commands

```bash
# List all milestones (sorted by priority)
taskpy milestones

# Show milestone details and progress
taskpy milestone show milestone-1

# Mark milestone as active (multiple can be active)
taskpy milestone start milestone-2

# Mark milestone as completed
taskpy milestone complete milestone-1

# Assign task to milestone
taskpy milestone assign FEAT-01 milestone-1

# Filter tasks by milestone
taskpy list --milestone milestone-1
taskpy stats --milestone milestone-1
```

## NFR Management

Define Non-Functional Requirements in `data/kanban/info/nfrs.toml`:

```toml
[NFR-SEC-001]
category = "SEC"
number = 1
title = "Code must be free of security vulnerabilities"
description = "No SQL injection, XSS, command injection, etc."
verification = "Run security linters"
default = true  # Auto-applied to all new tasks

[NFR-PERF-001]
category = "PERF"
number = 1
title = "Operations must complete in <100ms"
description = "Critical path operations under 100ms"
verification = "cargo bench"
default = false  # Manually applied
```

## Workflow

```
stub → backlog → ready → in_progress → qa → done → archived
 ↑        ↑        ↑           ↑        ↑      ↑
 └────────┴────────┴───────────┴────────┴──────┘
            (tasks can move backwards)

                    blocked (special state)
                       ↕
              (can block from any status)
```

### Workflow Commands

```bash
# Create task (starts in stub by default)
taskpy create FEAT "My feature"

# Promote through workflow
taskpy promote FEAT-01        # stub → backlog
taskpy promote FEAT-01        # backlog → ready
taskpy promote FEAT-01        # ready → in_progress
taskpy promote FEAT-01        # in_progress → qa
taskpy promote FEAT-01        # qa → done

# Move backwards
taskpy move FEAT-01 in_progress

# Skip to specific status
taskpy move FEAT-01 done

# Block task
taskpy move FEAT-01 blocked

# Archive completed tasks
taskpy move FEAT-01 archived

# Create task directly in backlog (skip stub)
taskpy create FEAT "Well-defined feature" --status backlog
```

## Integration with Other Tools

### TestPy Integration

```bash
# Link test command to task
taskpy link FEAT-001 --verify "testpy run --language rust"

# Run verification
taskpy verify FEAT-001 --update
```

### FeatPy Integration

```bash
# After implementing a feature, update feature docs
featpy sync

# Link feature docs to task
taskpy link FEAT-001 --docs docs/features/FEAT_AUTH.md
```

### Git Integration

```bash
# Use task IDs in commit messages
git commit -m "feat(FEAT-001): implement user authentication"

# Track commits in session
taskpy session commit abc123 "Added JWT token validation"
```

## Querying Tasks

### List Filtering

```bash
# By epic
taskpy list --epic BUGS

# By status
taskpy list --status in_progress

# By priority
taskpy list --priority critical

# By milestone
taskpy list --milestone milestone-1

# By tags
taskpy list --tags security,auth

# Combined filters
taskpy list --epic FEAT --status in_progress --priority high --milestone milestone-1
```

### Output Formats

```bash
# Pretty table (default)
taskpy list

# Task cards (detailed)
taskpy list --format cards

# Just IDs (for scripting)
taskpy list --format ids

# TSV (for processing)
taskpy list --format tsv

# Plain data mode (no boxy)
taskpy --view=data list
taskpy --no-boxy list
```

## Statistics

```bash
# Overall stats
taskpy stats

# Epic-specific stats
taskpy stats --epic FEAT
```

Output example:
```
==================================================
Task Statistics
==================================================

Total Tasks: 42
Total Story Points: 137

By Status:
  backlog          15
  ready             5
  in_progress       8
  review            3
  done             11

By Priority:
  critical          2
  high             12
  medium           20
  low               8
```

## Kanban Board

```bash
# Show all tasks
taskpy kanban

# Filter by epic
taskpy kanban --epic FEAT
```

## Configuration

Edit `data/kanban/info/config.toml`:

```toml
[general]
default_story_points = 0
apply_default_nfrs = true
default_priority = "medium"

[workflow]
statuses = ["stub", "backlog", "ready", "in_progress", "qa", "done", "archived"]
auto_archive_days = 0  # Auto-archive done tasks after N days

[verification]
require_tests = false  # Require tests to pass before moving to done

[display]
default_view = "pretty"
show_story_points = true
show_tags = true
```

## AI Agent Usage

TaskPy is designed for both human and AI agent use:

### Agent Workflow

```bash
# Agent starts session
taskpy session start --focus "Implement FEAT-001"

# Agent lists current work
taskpy list --status in_progress --assigned $SESSION_ID

# Agent shows task details
taskpy show FEAT-001

# Agent marks task complete
taskpy promote FEAT-001

# Agent verifies tests
taskpy verify FEAT-001 --update

# Agent ends session (auto-generates HANDOFF)
taskpy session end --notes "Completed authentication implementation"
```

### Data Mode for Scripting

Use `--view=data` for machine-readable output:

```bash
# Get task IDs for scripting
TASKS=$(taskpy --view=data list --status in_progress --format ids)

# Process with other tools
taskpy --view=data list --format tsv | awk -F'\t' '{print $1, $4}'
```

## Comparison: v3 vs v4

| Aspect | META PROCESS v3 | META PROCESS v4 (TaskPy) |
|--------|-----------------|--------------------------|
| Task tracking | Manual TASKS.txt | Structured markdown + manifest |
| Status updates | Manual editing | `taskpy promote/move` |
| Queries | Grep/manual search | Fast TSV index |
| Handoff | Manual HANDOFF.md | Auto-generated from sessions |
| Hygiene | Manual cleanup | Automatic (file moves) |
| References | Free-form text | Structured linking |
| Verification | Manual tracking | Integrated test hooks |
| Agent-friendly | Medium | High (structured data) |
| Git-friendly | Yes | Yes |

## Extending TaskPy

### Add Custom Epics

Edit `data/kanban/info/epics.toml`:

```toml
[DEPLOY]
description = "Deployment and infrastructure tasks"
active = true
```

Then use it:

```bash
taskpy create DEPLOY "Set up CI/CD pipeline" --sp 8
```

### Add Custom NFRs

Edit `data/kanban/info/nfrs.toml`:

```toml
[NFR-DOC-002]
category = "DOC"
number = 2
title = "All features must have user documentation"
description = "Update docs/ with user-facing documentation"
verification = "Check docs/ directory"
default = true
```

### Custom Verification Commands

```bash
# Rust projects
taskpy link FEAT-001 --verify "cargo test feature_name::"

# Python projects
taskpy link FEAT-001 --verify "pytest tests/test_feature.py"

# Shell scripts
taskpy link FEAT-001 --verify "./bin/test_feature.sh"

# Multi-step
taskpy link FEAT-001 --verify "cargo test && cargo clippy && cargo fmt --check"
```

## Roadmap

### Milestone 1: Foundation MVP (In Progress)
- [x] Milestone system with priority ordering
- [x] Stub/QA/Blocked status support
- [ ] Promotion gating and status lifecycle validation
- [ ] Blocking system for tasks and milestones
- [ ] Task demote command
- [ ] Rolo integration for better table formatting
- [ ] Validation warnings and boundary checks

### Milestone 2: Feature Complete (Planned)
- [ ] Sub-task support and hierarchy
- [ ] Subtask linking commands
- [ ] Task split command for breaking down large tasks
- [ ] Auto-incrementing sequence ID for sorting
- [ ] Session sprint selection and management
- [ ] Dynamic epic registration command

### Milestone 3: Polish and Release (Planned)
- [ ] Examples directory with real-world usage
- [ ] Enhanced documentation

### Milestone 4: Workflow Automation & HANDOFF (Future)
- [ ] Go-flow system (load/go/rem/fin commands)
- [ ] Work session time tracking
- [ ] Git snapshot and dirty state handling
- [ ] Task reminder and warning system
- [ ] History logging and audit trail
- [ ] HANDOFF generation commands (create/read)
- [ ] Dependency graph visualization
- [ ] Burndown charts and velocity tracking

### Future Considerations
- [ ] GitHub issues sync
- [ ] Template system for task content
- [ ] Export to JIRA/Linear/etc

## Contributing

See `docs/dev/CONTRIBUTING.md` for development guidelines.

## License

AGPLv3 - See LICENSE file

## Credits

Part of the SnekFX toolchain:
- **testpy** - Universal test orchestrator
- **featpy** - Feature documentation tool
- **taskpy** - Task management (this tool)

---

**TaskPy** - Making agile task management simple, structured, and automation-friendly.
