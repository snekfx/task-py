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
- ✅ **Kanban workflow** (backlog → ready → in_progress → review → done)
- ✅ **Story point tracking**
- ✅ **Priority management** (critical, high, medium, low)
- ✅ **NFR compliance** (link Non-Functional Requirements to tasks)
- ✅ **Reference linking** (code files, docs, test files, plans)
- ✅ **Test verification** (integrate with testpy/cargo test)
- ✅ **Pretty output** via boxy/rolo or plain data mode
- ✅ **Git-friendly** (plain text, human-readable)
- ✅ **Fast queries** via TSV manifest
- ✅ **Extensible** (TOML configuration for epics and NFRs)

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

# Create a task
taskpy create FEAT "Add user authentication" --sp 5 --priority high

# List tasks
taskpy list

# Show task details
taskpy show FEAT-001

# Edit task (opens in $EDITOR)
taskpy edit FEAT-001

# Move task through workflow
taskpy promote FEAT-001              # Move to next status
taskpy move FEAT-001 in_progress     # Move to specific status

# View kanban board
taskpy kanban

# Link references
taskpy link FEAT-001 --code src/auth.rs --test tests/auth_test.rs

# Run verification
taskpy verify FEAT-001

# Show statistics
taskpy stats
taskpy stats --epic FEAT
```

## Directory Structure

```
your-project/
├── data/kanban/              # TaskPy data (gitignored by default)
│   ├── info/
│   │   ├── epics.toml        # Epic definitions
│   │   ├── nfrs.toml         # NFR definitions
│   │   └── config.toml       # TaskPy config
│   ├── status/               # Task files organized by status
│   │   ├── backlog/
│   │   ├── ready/
│   │   ├── in_progress/
│   │   ├── review/
│   │   ├── done/
│   │   └── archived/
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
└── .gitignore                # Updated to exclude data/kanban/
```

## Task File Format

Tasks are stored as Markdown files with YAML frontmatter:

```markdown
---
id: FEAT-001
title: Add user authentication
epic: FEAT
number: 1
status: in_progress
story_points: 5
priority: high
created: 2025-11-15T12:00:00
updated: 2025-11-15T14:30:00
assigned: session-001
tags: [security, auth]
dependencies: []
blocks: [FEAT-002]
nfrs: [NFR-SEC-001, NFR-TEST-001]
references.code: [src/auth.rs, src/user.rs]
references.tests: [tests/auth_test.rs]
verification.command: cargo test auth::
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
backlog → ready → in_progress → review → done → archived
   ↑         ↑          ↑           ↑       ↑
   └─────────┴──────────┴───────────┴───────┘
         (tasks can move backwards)
```

### Workflow Commands

```bash
# Create task (starts in backlog)
taskpy create FEAT "My feature"

# Promote through workflow
taskpy promote FEAT-001        # backlog → ready
taskpy promote FEAT-001        # ready → in_progress
taskpy promote FEAT-001        # in_progress → review
taskpy promote FEAT-001        # review → done

# Move backwards
taskpy move FEAT-001 in_progress

# Skip to specific status
taskpy move FEAT-001 done

# Archive completed tasks
taskpy move FEAT-001 archived
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

# By tags
taskpy list --tags security,auth

# Combined filters
taskpy list --epic FEAT --status in_progress --priority high
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
statuses = ["backlog", "ready", "in_progress", "review", "done", "archived"]
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

- [ ] Session management with auto HANDOFF generation
- [ ] Rolo integration for better table formatting
- [ ] Dependency graph visualization
- [ ] Burndown charts and velocity tracking
- [ ] GitHub issues sync
- [ ] Template system for task content
- [ ] Sub-task support
- [ ] Time tracking
- [ ] Sprint planning helpers
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
