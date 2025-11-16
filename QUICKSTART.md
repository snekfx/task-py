# TaskPy Quick Start

Get started with TaskPy in 5 minutes!

## Installation

```bash
# Option 1: Install with pip (recommended)
pip install -e .

# Option 2: Install with pipx (isolated)
pipx install .

# Option 3: Run directly (development)
alias taskpy='PYTHONPATH=/path/to/task-py/src python3 -m taskpy'
```

## Basic Workflow

### 1. Initialize

```bash
cd your-project
taskpy init
```

This creates:
- `data/kanban/` - Task management structure
- `.gitignore` - Updated to exclude kanban data
- Default epics and NFRs

### 2. Create Your First Task

```bash
taskpy create FEAT "Implement user login" --sp 5 --priority high
# Created: FEAT-001
```

### 3. View Tasks

```bash
# List all tasks
taskpy list

# Show details
taskpy show FEAT-001

# Filter by epic
taskpy list --epic FEAT

# Filter by status
taskpy list --status in_progress
```

### 4. Move Tasks Through Workflow

```bash
# Promote to next status
taskpy promote FEAT-001   # backlog → ready
taskpy promote FEAT-001   # ready → in_progress
taskpy promote FEAT-001   # in_progress → review
taskpy promote FEAT-001   # review → done

# Or move directly
taskpy move FEAT-001 in_progress
```

### 5. View Kanban Board

```bash
taskpy kanban
```

### 6. Add References

```bash
# Link code files
taskpy link FEAT-001 --code src/auth.rs --code src/user.rs

# Link tests
taskpy link FEAT-001 --test tests/auth_test.rs

# Link documentation
taskpy link FEAT-001 --docs docs/auth.md

# Link plans
taskpy link FEAT-001 --plan PLAN-001
```

### 7. Set Up Verification

```bash
# Add test command
taskpy link FEAT-001 --verify "cargo test auth::"

# Run verification
taskpy verify FEAT-001 --update
```

### 8. View Statistics

```bash
# All tasks
taskpy stats

# By epic
taskpy stats --epic FEAT
```

## Common Patterns

### Bug Fixing Workflow

```bash
# 1. Create bug task
taskpy create BUGS "Fix null pointer in auth" --sp 2 --priority critical

# 2. Link to code
taskpy link BUGS-001 --code src/auth.rs:42

# 3. Move to in progress
taskpy move BUGS-001 in_progress

# 4. Fix and test
# ... make changes ...

# 5. Add verification
taskpy link BUGS-001 --verify "cargo test --lib auth::tests"
taskpy verify BUGS-001 --update

# 6. Mark done
taskpy promote BUGS-001
```

### Feature Development

```bash
# 1. Create feature
taskpy create FEAT "Add dark mode" --sp 8 --priority medium --tags ui,ux

# 2. Link plan document
taskpy link FEAT-001 --plan docs/plan/PLAN-DARK-MODE.md

# 3. Link code as you develop
taskpy link FEAT-001 --code src/theme.rs
taskpy link FEAT-001 --code src/ui/settings.rs

# 4. Link tests
taskpy link FEAT-001 --test tests/theme_test.rs

# 5. Verify NFRs
taskpy show FEAT-001  # Check NFRs are linked
taskpy verify FEAT-001 --update

# 6. Complete
taskpy promote FEAT-001
```

### Documentation Work

```bash
taskpy create DOCS "Write REST API documentation" --sp 3
taskpy link DOCS-001 --docs docs/api/
taskpy move DOCS-001 in_progress
# ... write docs ...
taskpy move DOCS-001 done
```

## Output Modes

### Pretty Mode (default)
Uses boxy for beautiful terminal output:
```bash
taskpy list
taskpy show FEAT-001
```

### Data Mode (scripting/AI)
Plain text output for processing:
```bash
taskpy --view=data list
taskpy --no-boxy list --format tsv
```

## Customization

### Add Custom Epic

Edit `data/kanban/info/epics.toml`:
```toml
[DEPLOY]
description = "Deployment tasks"
active = true
```

Then use it:
```bash
taskpy create DEPLOY "Set up production environment" --sp 13
```

### Add Custom NFR

Edit `data/kanban/info/nfrs.toml`:
```toml
[NFR-PERF-001]
category = "PERF"
number = 1
title = "Response time under 100ms"
description = "All API endpoints must respond in <100ms"
verification = "cargo bench"
default = false
```

Link to tasks:
```bash
taskpy link FEAT-001 --nfr NFR-PERF-001
```

## Scripting Examples

### List all in-progress tasks
```bash
taskpy --view=data list --status in_progress --format ids
```

### Get task count by epic
```bash
taskpy --view=data list --format tsv | awk -F'\t' '{print $2}' | sort | uniq -c
```

### Find high-priority backlog
```bash
taskpy --view=data list --status backlog --priority high --format tsv
```

## Integration with Git

### Commit messages
```bash
# Use task IDs in commits
git commit -m "feat(FEAT-001): implement dark mode toggle"
git commit -m "fix(BUGS-001): handle null pointer in auth"
```

### Pre-commit hook
Create `.git/hooks/pre-commit`:
```bash
#!/bin/bash
# Verify all in-progress tasks have tests
IN_PROGRESS=$(taskpy --view=data list --status in_progress --format ids)
for task in $IN_PROGRESS; do
    if ! taskpy verify $task 2>/dev/null; then
        echo "Warning: $task tests not passing"
    fi
done
```

## Next Steps

1. **Read the full README.md** for detailed documentation
2. **Customize epics** in `data/kanban/info/epics.toml`
3. **Review NFRs** in `data/kanban/info/nfrs.toml`
4. **Set up verification** for your test runner
5. **Integrate with CI/CD** for automated task tracking

## Getting Help

```bash
# Command help
taskpy --help
taskpy create --help
taskpy list --help

# List available epics
taskpy epics

# List NFRs
taskpy nfrs
taskpy nfrs --defaults
```

## Troubleshooting

**TaskPy not initialized:**
```bash
taskpy init
```

**Unknown epic:**
```bash
taskpy epics  # See available epics
# Or add to data/kanban/info/epics.toml
```

**Can't find task:**
```bash
taskpy list --format ids  # List all task IDs
```

**Verification failed:**
```bash
taskpy show TASK-ID  # Check verification command
taskpy verify TASK-ID  # Run manually to see output
```

---

Happy task tracking! 🚀
