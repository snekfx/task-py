# Display Module Migration Reference

## Overview
Complete migration of display/visualization commands from `legacy/commands.py` to `modern/display/` module.

**Status**: Not started (stub only)

**Tracking Task**: REF-15

**Related Tasks**: REF-10 (Large features migration)

**Priority**: MEDIUM - Display commands are useful for visualization but less critical than core CRUD

## Legacy Code Locations

All display commands in: `src/taskpy/legacy/commands.py`

### Main Functions

| Function | Lines | Description | Status |
|----------|-------|-------------|--------|
| `cmd_info(args)` | 800-845 | Show task status and gate requirements | ❌ Not migrated |
| `cmd_stoplight(args)` | 846-900 | Validate gates with exit code | ❌ Not migrated |
| `cmd_kanban(args)` | 901-935 | Display kanban board | ❌ Not migrated |
| `cmd_history(args)` | 1196-1305 | Display task history/audit trail | ❌ Not migrated |
| `cmd_stats(args)` | TBD | Show project statistics | ❌ Need to locate |

### Helper Functions

| Function | Purpose |
|----------|---------|
| `display_kanban_column(status, tasks)` | Render single kanban column |
| `_sort_tasks(tasks, mode)` | Sort tasks by priority/created/updated |
| `_read_manifest()` | Load all tasks from manifest |
| `validate_promotion(task, next_status, commit_hash)` | Check gate requirements (for info/stoplight) |

## Dependencies

**Internal dependencies**:
- `TaskStorage` - all storage operations
- `_read_manifest()` - task loading
- `validate_promotion()` - gate validation (for info/stoplight)
- `print_success/error/info/warning` - output utilities
- `ListView` - modern table rendering (can enhance displays)
- Modern views for better visualization

**External tools**:
- Boxy for box rendering (kanban, stats)
- Rolo for table rendering

## Command API Structure

### Current Legacy API
```bash
taskpy info TASK-ID                  # Show gate requirements for next promotion
taskpy stoplight TASK-ID             # Validate gates with exit code (0=ready, 1=blocked, 2=error)
taskpy kanban [--epic EPIC] [--sort MODE]  # Display kanban board
taskpy history TASK-ID [--all]       # Show task history
taskpy stats [--epic EPIC]           # Show project statistics
```

### Target Modern API
```bash
taskpy modern info TASK-ID
taskpy modern stoplight TASK-ID
taskpy modern kanban [--epic EPIC] [--sort MODE]
taskpy modern history TASK-ID [--all]
taskpy modern stats [--epic EPIC]
```

## Migration Tasks

### Phase 1: Status Display (REF-15a) - 1 SP
- [ ] Migrate `cmd_info()` - Show gate requirements
  - Current status display
  - Next status in workflow
  - Gate requirement checklist
  - Use show_card() for better formatting
- [ ] Migrate `cmd_stoplight()` - Gate validation with exit codes
  - Exit 0 if ready to promote
  - Exit 1 if missing requirements
  - Exit 2 if blocked or error
  - Used by automation/CI systems

### Phase 2: Visualization (REF-15b) - 1 SP
- [ ] Migrate `cmd_kanban()` - Kanban board display
  - Group tasks by status columns
  - Filter by epic
  - Sort within columns
  - Use ListView for column rendering
  - Use boxy for column boxes
- [ ] Locate and migrate `cmd_stats()` - Project statistics
  - Task counts by status
  - Story point totals
  - Completion percentages
  - Burndown data
  - Use rolo_table for display

### Phase 3: History & Audit (REF-15c) - 0.5 SP
- [ ] Migrate `cmd_history()` - Task history display
  - Single task mode: show task history
  - All mode (--all): show all task history
  - Timeline formatting
  - Action/transition display
  - Reason/actor/metadata display

### Phase 4: Testing & Integration (REF-15d) - 0.5 SP
- [ ] Create tests for each display command
- [ ] Test with various data scenarios
- [ ] Test stoplight exit codes
- [ ] Verify legacy commands still work
- [ ] Integration tests

## Key Implementation Notes

### Info Command Pattern
```python
# From legacy cmd_info (lines 800-845)
# 1. Load task and get current status
# 2. Determine next status in workflow
# 3. Display task info (ID, status, title)
# 4. Call validate_promotion() for next status
# 5. Display gate requirements:
#    - ✅ Ready to promote (all requirements met)
#    - Or list of blockers
```

### Stoplight Command Pattern
```python
# From legacy cmd_stoplight (lines 846-900)
# Used by automation/CI for gate checks
# Exit codes:
#   0 - Ready to promote (all gates passed)
#   1 - Missing requirements (gate failure)
#   2 - Blocked or error
#
# 1. Check if task is BLOCKED status
#    - If blocked: print reason, exit 2
# 2. Determine next status in workflow
# 3. Call validate_promotion()
# 4. Exit with appropriate code
```

### Kanban Command Pattern
```python
# From legacy cmd_kanban (lines 901-935)
# 1. Load all tasks from manifest
# 2. Filter by epic if specified
# 3. Group tasks by status (columns)
# 4. Sort tasks within each column by --sort mode
# 5. Display each column:
#    - Column header (status name)
#    - Task list (ID, title, SP, priority)
#    - Use display_kanban_column() helper
# 6. Consider using ListView for better formatting
```

### History Command Pattern
```python
# From legacy cmd_history (lines 1196-1305)
# Two modes:
# 1. Single task (TASK-ID):
#    - Load task
#    - Display task.history entries
#    - Format: timestamp, action, transition, reason, actor
# 2. All tasks (--all):
#    - Load all tasks from manifest
#    - Collect tasks with history
#    - Display all history grouped by task
#    - Summary: N tasks, M total entries
```

### Stats Command Pattern
```python
# Need to locate cmd_stats() in legacy code
# Expected features:
# - Total task counts
# - Breakdown by status
# - Total story points
# - Story points by status
# - Completion percentage
# - Epic-specific stats if filtered
# - Use rolo_table for tabular display
```

## Data Structures

### Task History Entry
```python
class HistoryEntry:
    timestamp: datetime       # When action occurred
    action: str              # Action type (promote, demote, create, etc.)
    from_status: str         # Previous status (for transitions)
    to_status: str           # New status (for transitions)
    reason: str              # Optional reason
    actor: str               # Who performed action
    metadata: dict           # Additional context
```

### Kanban Display Structure
```python
# Tasks grouped by status
kanban_data = {
    TaskStatus.STUB: [task1, task2, ...],
    TaskStatus.BACKLOG: [...],
    TaskStatus.READY: [...],
    TaskStatus.ACTIVE: [...],
    TaskStatus.QA: [...],
    TaskStatus.DONE: [...]
}
```

### Gate Validation Result
```python
# From validate_promotion()
is_valid: bool              # True if ready to promote
blockers: List[str]         # List of blocking requirements
```

## Testing Strategy

### Unit Tests
- Test info with various gate states
- Test stoplight exit codes (0, 1, 2)
- Test kanban with filters and sorting
- Test history with single and all modes
- Test stats calculations

### Integration Tests
- Full workflow display: info → promote → history
- Kanban filtering by epic
- History across multiple status transitions
- Stats aggregation accuracy

### Edge Cases
- Info for task at final status (done)
- Stoplight for blocked task
- Kanban with empty status columns
- History for task with no history
- Stats with no tasks
- Stoplight for task not found (exit 2)

## Migration Checklist

- [ ] Create `modern/display/` module directory
- [ ] Migrate `cmd_info()` to `modern/display/commands.py`
- [ ] Migrate `cmd_stoplight()` with correct exit codes
- [ ] Migrate `cmd_kanban()` with ListView integration
- [ ] Locate and migrate `cmd_stats()`
- [ ] Migrate `cmd_history()` with both modes
- [ ] Create `modern/display/cli.py` with command registration
- [ ] Update `modern/cli.py` to register display module
- [ ] Create comprehensive test suite
- [ ] Link code references to REF-15
- [ ] Update verification commands
- [ ] Test backward compatibility

## Estimated Effort

**Total: 3 SP** (REF-15)

Breakdown:
- Status display (info/stoplight): 1 SP
- Visualization (kanban/stats): 1 SP
- History & audit: 0.5 SP
- Testing & integration: 0.5 SP

## Dependencies & Blockers

**Dependencies**:
- ListView (already available)
- Boxy integration (already working)
- Rolo table rendering (already available)

**Blockers**:
- Need to locate cmd_stats() in legacy code

**Nice to have**:
- Enhanced kanban with swimlanes
- Chart rendering for stats (burndown, velocity)
- History filtering and search
- Export history to CSV/JSON
- Interactive kanban (terminal UI)
