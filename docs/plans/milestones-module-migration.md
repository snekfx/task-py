# Milestones Module Migration Reference

## Overview
Complete migration of milestones management commands from `legacy/commands.py` to `modern/milestones/` module.

**Status**: Not started (stub only)

**Tracking Task**: REF-17

**Related Tasks**: REF-08 (Small features migration)

**Priority**: LOW - Milestones are useful but less critical than core functionality

## Legacy Code Locations

All milestones commands in: `src/taskpy/legacy/commands.py`

### Main Functions

| Function | Lines | Description | Status |
|----------|-------|-------------|--------|
| `cmd_milestones(args)` | 2273-2311 | List all milestones | ❌ Not migrated |
| `cmd_milestone(args)` | 2313-2332 | Route milestone subcommands | ❌ Not migrated |
| `_cmd_milestone_show(args)` | TBD | Show milestone details | ❌ Not migrated |
| `_cmd_milestone_start(args)` | TBD | Start milestone | ❌ Not migrated |
| `_cmd_milestone_complete(args)` | TBD | Complete milestone | ❌ Not migrated |
| `_cmd_milestone_assign(args)` | TBD | Assign task to milestone | ❌ Not migrated |

### Helper Functions

| Function | Purpose |
|----------|---------|
| `storage.load_milestones()` | Load milestones from milestones.toml |

## Dependencies

**Internal dependencies**:
- `TaskStorage` - storage operations
- `print_success/error/info/warning` - output utilities
- `ListView` - modern table rendering
- Milestone model (need to check if defined)

**External tools**:
- TOML config file: `data/kanban/info/milestones.toml`

## Command API Structure

### Current Legacy API
```bash
taskpy milestones                        # List all milestones
taskpy milestone show MILESTONE-ID       # Show milestone details
taskpy milestone start MILESTONE-ID      # Start milestone
taskpy milestone complete MILESTONE-ID   # Complete milestone
taskpy milestone assign TASK-ID MILESTONE-ID  # Assign task to milestone
```

### Target Modern API
```bash
taskpy modern milestones
taskpy modern milestone show MILESTONE-ID
taskpy modern milestone start MILESTONE-ID
taskpy modern milestone complete MILESTONE-ID
taskpy modern milestone assign TASK-ID MILESTONE-ID
```

## Migration Tasks

### Phase 1: List & Show (REF-17a) - 0.5 SP
- [ ] Migrate `cmd_milestones()` - List all milestones
  - Load from milestones.toml
  - Sort by priority
  - Display with status icons
  - Use ListView for better formatting
- [ ] Locate and migrate `_cmd_milestone_show()` - Show details
  - Display milestone info
  - Show assigned tasks
  - Show progress (completed/total SP)

### Phase 2: Milestone Management (REF-17b) - 1 SP
- [ ] Locate and migrate `_cmd_milestone_start()` - Start milestone
  - Update status to 'active'
  - Save to milestones.toml
- [ ] Locate and migrate `_cmd_milestone_complete()` - Complete milestone
  - Update status to 'completed'
  - Save to milestones.toml
- [ ] Locate and migrate `_cmd_milestone_assign()` - Assign task
  - Update task.milestone field
  - Save task

### Phase 3: Testing & Integration (REF-17c) - 0.5 SP
- [ ] Create tests for milestone commands
- [ ] Test TOML loading/saving
- [ ] Verify legacy commands still work
- [ ] Integration tests

## Key Implementation Notes

### Milestones List Pattern
```python
# From legacy cmd_milestones (lines 2273-2311)
# 1. Load milestones from storage.load_milestones()
# 2. Check if empty
# 3. Sort by priority
# 4. Display each milestone:
#    - Status icon (🟢 active, ⚪ planned, 🔴 blocked, ✅ completed)
#    - [ID] Name
#    - Priority | Status
#    - Goal: N SP (if set)
#    - Description
#    - Blocked reason (if blocked)
# 5. Consider using ListView for better formatting
```

### Milestone Router Pattern
```python
# From legacy cmd_milestone (lines 2313-2332)
# Router pattern similar to sprint:
# 1. Check for milestone_command arg
# 2. Dispatch to subcommand handler:
#    - show: _cmd_milestone_show()
#    - start: _cmd_milestone_start()
#    - complete: _cmd_milestone_complete()
#    - assign: _cmd_milestone_assign()
# 3. Error if unknown subcommand
```

### Milestone Show Pattern
```python
# Need to locate _cmd_milestone_show() implementation
# Expected:
# 1. Load milestone from milestones.toml
# 2. Display milestone details (name, status, goal, description)
# 3. Load all tasks assigned to this milestone
# 4. Display task list
# 5. Show progress: X/Y SP completed
```

### Milestone Assign Pattern
```python
# Need to locate _cmd_milestone_assign() implementation
# Expected:
# 1. Find task by ID
# 2. Validate milestone exists
# 3. Set task.milestone = milestone_id
# 4. Save task
# 5. Print success
```

## Data Structures

### Milestones Config (milestones.toml)
```toml
[M1]
name = "MVP Release"
description = "Core features for initial release"
status = "active"  # active, planned, blocked, completed
priority = 1
goal_sp = 40
blocked_reason = ""  # Set if status is blocked

[M2]
name = "Beta Release"
description = "Additional features for beta"
status = "planned"
priority = 2
goal_sp = 80
blocked_reason = ""
```

### Milestone Model
```python
class Milestone:
    id: str              # Milestone ID (M1, M2, etc.)
    name: str            # Display name
    description: str     # Detailed description
    status: str          # active, planned, blocked, completed
    priority: int        # Sort order
    goal_sp: int         # Target story points (optional)
    blocked_reason: str  # Reason if blocked (optional)
```

### Task Milestone Field
```yaml
milestone: M1  # Milestone assignment (optional)
```

## Testing Strategy

### Unit Tests
- Test milestones list with various statuses
- Test milestone show with assigned tasks
- Test milestone start/complete status transitions
- Test milestone assign with valid/invalid IDs
- Test TOML parsing and saving

### Integration Tests
- Full milestone workflow: create → start → assign tasks → complete
- Test with multiple milestones
- Test milestone filtering in task list

### Edge Cases
- List with no milestones defined
- Show with no assigned tasks
- Assign to non-existent milestone
- Complete milestone with incomplete tasks
- Start already active milestone

## Migration Checklist

- [ ] Locate milestone subcommand implementations
- [ ] Create `modern/milestones/` module directory
- [ ] Migrate `cmd_milestones()` to `modern/milestones/commands.py`
- [ ] Migrate `cmd_milestone()` router
- [ ] Migrate all subcommand handlers
- [ ] Create `modern/milestones/cli.py` with command registration
- [ ] Update `modern/cli.py` to register milestones module
- [ ] Create comprehensive test suite
- [ ] Link code references to REF-17
- [ ] Update verification commands
- [ ] Test backward compatibility

## Estimated Effort

**Total: 2 SP** (REF-17)

Breakdown:
- List & show: 0.5 SP
- Milestone management (start/complete/assign): 1 SP
- Testing & integration: 0.5 SP

## Dependencies & Blockers

**Dependencies**:
- Milestone model definition
- TOML config file template

**Blockers**:
- Need to locate subcommand implementations

**Nice to have**:
- Milestone progress visualization
- Burndown charts per milestone
- Milestone dependencies/ordering
- Auto-milestone based on task patterns
