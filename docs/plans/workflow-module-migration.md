# Workflow Module Migration Reference

## Overview
Complete migration of workflow commands (promote, demote, move) from `legacy/commands.py` to `modern/workflow/` module.

**Status**: Not started (stub only)

**Tracking Task**: REF-14

**Related Tasks**: REF-09 (Medium features migration)

**Priority**: MEDIUM - Workflow commands are frequently used for task status transitions

## Legacy Code Locations

All workflow commands in: `src/taskpy/legacy/commands.py`

### Main Functions

| Function | Lines | Description | Status |
|----------|-------|-------------|--------|
| `cmd_promote(args)` | 571-643 | Move task forward in workflow | ❌ Not migrated |
| `cmd_demote(args)` | 644-726 | Move task backwards with reason | ❌ Not migrated |
| `cmd_move(args)` | 727-799 | Move task to specific status | ❌ Not migrated |

### Helper Functions

| Function | Purpose |
|----------|---------|
| `_move_task(storage, task_id, path, target_status, task, reason, action)` | Core task movement logic |
| `validate_promotion(task, target_status, commit_hash)` | Check gate requirements for promotion |
| `validate_done_demotion(task, reason)` | Validate demotion from done status |
| `log_override(storage, task_id, from_status, to_status, reason)` | Log override actions |
| `parse_task_ids(task_ids)` | Parse task IDs from various formats |

## Dependencies

**Internal dependencies**:
- `TaskStorage` - all storage operations
- `TaskStatus` enum - status definitions
- `validate_promotion()` - gate validation logic
- `validate_done_demotion()` - done demotion validation
- `print_success/error/info/warning` - output utilities
- Modern views (for potential visual workflow display)

**External tools**:
- Override logging to `data/kanban/info/override_log.txt`

## Command API Structure

### Current Legacy API
```bash
taskpy promote TASK-ID [--target-status STATUS] [--commit HASH] [--override] [--reason REASON]
taskpy demote TASK-ID [--to STATUS] [--reason REASON] [--override]
taskpy move TASK-ID[,TASK-ID...] STATUS --reason REASON
```

### Target Modern API
```bash
taskpy modern promote TASK-ID [--target-status STATUS] [--commit HASH] [--override] [--reason REASON]
taskpy modern demote TASK-ID [--to STATUS] [--reason REASON] [--override]
taskpy modern move TASK-ID[,TASK-ID...] STATUS --reason REASON
```

## Migration Tasks

### Phase 1: Core Movement Logic (REF-14a) - 1 SP
- [ ] Migrate `_move_task()` helper - Core task movement
- [ ] Migrate `validate_promotion()` - Gate validation
- [ ] Migrate `validate_done_demotion()` - Done validation
- [ ] Migrate `log_override()` - Override logging
- [ ] Migrate `parse_task_ids()` - Task ID parsing

### Phase 2: Workflow Commands (REF-14b) - 1.5 SP
- [ ] Migrate `cmd_promote()` - Forward workflow transitions
  - Standard workflow progression
  - REGRESSION → QA special case
  - Override flag support
  - Gate validation
  - Commit hash tracking
- [ ] Migrate `cmd_demote()` - Backward workflow transitions
  - QA → REGRESSION special case
  - Done demotion with reason requirement
  - Override flag support
- [ ] Migrate `cmd_move()` - Direct status moves
  - Batch operation support
  - Reason requirement
  - Workflow transition warnings

### Phase 3: Testing & Integration (REF-14c) - 0.5 SP
- [ ] Create tests for each workflow command
- [ ] Test gate validation logic
- [ ] Test override logging
- [ ] Verify legacy commands still work
- [ ] Integration tests for full workflow

## Key Implementation Notes

### Workflow Order
```python
# Standard workflow progression
workflow = [
    TaskStatus.STUB,
    TaskStatus.BACKLOG,
    TaskStatus.READY,
    TaskStatus.ACTIVE,
    TaskStatus.QA,
    TaskStatus.DONE
]

# Special statuses outside main workflow:
# - REGRESSION: Failed QA, needs rework
# - BLOCKED: Blocked by external dependency
```

### Promote Pattern
```python
# From legacy cmd_promote (lines 571-643)
# 1. Find task and get current status
# 2. Determine target status:
#    - REGRESSION → QA (special case for re-review)
#    - Otherwise: next in workflow
#    - Or: explicit --target-status flag
# 3. Check for --override flag:
#    - If override: log to override_log.txt and skip validation
#    - Otherwise: validate_promotion()
# 4. Set commit_hash if provided
# 5. Call _move_task() with action="promote" or "override_promote"
```

### Demote Pattern
```python
# From legacy cmd_demote (lines 644-726)
# 1. Find task and get current status
# 2. Check for --override flag:
#    - If override: log to override_log.txt and skip validation
#    - Otherwise: validate_done_demotion() if from DONE
# 3. Determine target status:
#    - QA → REGRESSION (special case for failed QA)
#    - REGRESSION → ACTIVE (rework needed)
#    - Otherwise: previous in workflow
#    - Or: explicit --to flag
# 4. Set demotion_reason if demoting from DONE
# 5. Call _move_task() with action="demote" or "override_demote"
```

### Move Pattern
```python
# From legacy cmd_move (lines 727-799)
# 1. Require --reason flag (otherwise suggest promote/demote)
# 2. Parse task IDs (supports comma-delimited batch operations)
# 3. For each task:
#    - Find task and get current status
#    - Warn if looks like workflow transition
#    - Call _move_task() with action="move"
# 4. Print summary for batch operations
# 5. Exit with error code if any failures
```

### Gate Validation
```python
# Gate requirements by target status:
# STUB → BACKLOG: none
# BACKLOG → READY: acceptance criteria defined
# READY → ACTIVE: assignee set
# ACTIVE → QA: commit_hash set (code linked)
# QA → DONE: verification passing
```

## Data Structures

### Override Log Entry
Stored in: `data/kanban/info/override_log.txt`

```
2025-11-17 14:30:00 | TASK-ID | from_status → to_status | Reason: reason text
```

### Task Fields Updated
```yaml
status: new_status          # Updated by all commands
commit_hash: abc123          # Set by promote --commit
demotion_reason: reason text # Set by demote from DONE
```

## Testing Strategy

### Unit Tests
- Test promote with each workflow transition
- Test demote with REGRESSION and DONE special cases
- Test move with batch operations
- Test override flag logging
- Test gate validation logic

### Integration Tests
- Full workflow: stub → backlog → ready → active → qa → done
- Regression workflow: qa → regression → active → qa → done
- Override workflow: promote/demote with --override flag
- Batch move operations with mixed success/failure

### Edge Cases
- Promoting from final status (done)
- Demoting from initial status (stub)
- Moving to same status (noop)
- Override without reason
- Demoting from done without reason
- Promoting without required fields (gate validation)
- Batch move with some invalid task IDs

## Migration Checklist

- [ ] Create `modern/workflow/` module directory
- [ ] Migrate helper functions to `modern/workflow/commands.py`
- [ ] Migrate `cmd_promote()` with gate validation
- [ ] Migrate `cmd_demote()` with reason requirements
- [ ] Migrate `cmd_move()` with batch support
- [ ] Create `modern/workflow/cli.py` with command registration
- [ ] Update `modern/cli.py` to register workflow module
- [ ] Create comprehensive test suite
- [ ] Link code references to REF-14
- [ ] Update verification commands
- [ ] Test backward compatibility

## Estimated Effort

**Total: 3 SP** (REF-14)

Breakdown:
- Core movement logic & helpers: 1 SP
- Workflow commands (promote/demote/move): 1.5 SP
- Testing & integration: 0.5 SP

## Dependencies & Blockers

**Dependencies**:
- Gate validation logic (already in legacy)
- Override logging (already implemented)

**Blockers**:
- None

**Nice to have**:
- Visual workflow diagram display
- Workflow transition history tracking
- Gate requirement preview before promotion
- Batch promote/demote operations
