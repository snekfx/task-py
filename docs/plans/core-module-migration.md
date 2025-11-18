# Core Module Migration Reference

## Overview
Complete migration of core task CRUD commands from `legacy/commands.py` to `modern/core/` module.

**Status**: Partial (only `list` completed in FEAT-54)

**Tracking Task**: REF-13

**Related Tasks**: REF-10 (Large features migration)

**Priority**: HIGH - Core commands are most frequently used

## Legacy Code Locations

All core commands in: `src/taskpy/legacy/commands.py`

### Main Functions

| Function | Lines | Description | Status |
|----------|-------|-------------|--------|
| `cmd_create(args)` | 260-417 | Create new task | ❌ Not migrated |
| `cmd_list(args)` | 418-475 | List tasks with filters | ✅ Migrated (FEAT-54) |
| `cmd_show(args)` | 477-552 | Display task details | ❌ Not migrated |
| `cmd_edit(args)` | 553-570 | Edit task in $EDITOR | ❌ Not migrated |
| `cmd_rename(args)` | 2748-2832 | Rename task ID | ❌ Not migrated |

**Note**: Delete/recover functionality appears to be in trash/delete commands (need to locate)

### Helper Functions

| Function | Purpose |
|----------|---------|
| `_read_manifest(storage)` | Load all tasks from manifest |
| `_read_manifest_with_filters(storage, args)` | Load tasks with filtering |
| `_sort_tasks(tasks, mode)` | Sort tasks by various criteria |
| `_format_title_column(title)` | Format title for display |
| `_manifest_row_to_table(task)` | Convert task to table row |
| `_get_next_task_number(storage, epic)` | Get next available task number |
| `_validate_epic_exists(storage, epic)` | Check if epic is valid |

## Dependencies

**Internal dependencies**:
- `TaskStorage` - all storage operations
- `Task`, `TaskStatus`, `Priority` models
- `print_success/error/info/warning` - output utilities
- `ListView` - modern table rendering (already in list)
- `display_task_card` or `show_card` - card rendering for show command

**External dependencies**:
- `$EDITOR` environment variable (for edit command)
- File system operations for task files

## Command API Structure

### Current Legacy API
```bash
taskpy create EPIC "Title" --sp N --priority P [--milestone M]
taskpy list [--status S] [--epic E] [--priority P] [--milestone M] [--sort MODE]
taskpy show TASK-ID [TASK-ID...]
taskpy edit TASK-ID
taskpy rename TASK-ID NEW-ID
```

### Target Modern API
```bash
taskpy modern create EPIC "Title" --sp N --priority P [--milestone M]
taskpy modern list [--status S] [--epic E]    # ✅ Already works
taskpy modern show TASK-ID [TASK-ID...]
taskpy modern edit TASK-ID
taskpy modern rename TASK-ID NEW-ID
```

## Migration Tasks

### Phase 1: Read Operations (REF-13a) - 1 SP
- [x] `list` command - DONE (FEAT-54)
- [ ] `show` command - Display task card(s)
  - Single task: use `show_card()` from modern/views
  - Multiple tasks: loop and display each
  - Support both DATA and PRETTY modes

### Phase 2: Create Operation (REF-13b) - 2 SP
- [ ] Migrate `cmd_create()` - Most complex, lots of validation
  - Epic validation
  - Task number assignment
  - File creation
  - Manifest update
  - NFR defaults
  - Milestone assignment
  - Story point validation
  - Priority assignment

### Phase 3: Update Operations (REF-13c) - 1.5 SP
- [ ] Migrate `cmd_edit()` - Editor integration
  - Load task
  - Open in $EDITOR
  - Parse modified YAML
  - Validate changes
  - Save to storage
- [ ] Migrate `cmd_rename()` - ID reassignment
  - Complex: changes filename, updates references
  - Need to update manifest
  - Update any linked tasks

### Phase 4: Delete/Recover Operations (REF-13d) - 0.5 SP
- [ ] Locate delete/trash/recover functions
- [ ] Migrate to modern/core
- [ ] Implement soft delete (move to trash)
- [ ] Implement recovery from trash

## Key Implementation Notes

### Create Command Pattern
```python
# From legacy cmd_create (lines 260-417)
# 1. Validate epic exists
# 2. Get next task number for epic
# 3. Create Task model with all fields
# 4. Apply default NFRs
# 5. Create task file in correct status directory
# 6. Update manifest
# 7. Print success with next steps
```

### Show Command Pattern
```python
# From legacy cmd_show (lines 477-552)
# 1. Parse task IDs from args
# 2. Load each task
# 3. Convert to dict format
# 4. Use show_card() for display
# 5. Handle multiple tasks (loop)
# 6. Support --data mode (plain output)
```

### Edit Command Pattern
```python
# From legacy cmd_edit (lines 553-570)
# 1. Load task
# 2. Get task file path
# 3. Spawn $EDITOR with file
# 4. Wait for editor to close
# 5. Reload task from file
# 6. Validate YAML
# 7. Update manifest if needed
```

### Rename Command Pattern
```python
# From legacy cmd_rename (lines 2748-2832)
# Complex operation:
# 1. Validate new ID format
# 2. Check new ID doesn't exist
# 3. Load old task
# 4. Create new file with new ID
# 5. Delete old file
# 6. Update manifest (change ID)
# 7. Update any tasks that reference this ID
# 8. Print success
```

## Data Structures

### Task Creation Input
```python
args.epic         # Epic name (required)
args.title        # Task title (required)
args.story_points # Story points (optional)
args.priority     # Priority level (optional, default: medium)
args.milestone    # Milestone assignment (optional)
args.tags         # Comma-separated tags (optional)
args.assigned     # Assignee (optional)
```

### Task Display Output
```yaml
# Full task card format (show command)
ID: FEAT-01
Title: Add user authentication
Epic: FEAT
Status: active
Priority: high
Story Points: 5
Milestone: M1
Tags: security, auth
Created: 2025-11-17
Updated: 2025-11-18
---
# Description content here
```

## Testing Strategy

### Unit Tests
- Test create with various parameter combinations
- Test show with single and multiple tasks
- Test edit with valid/invalid YAML
- Test rename with ID format validation

### Integration Tests
- Full CRUD workflow: create → show → edit → rename
- Test with different epics and statuses
- Test error handling (invalid IDs, missing tasks)

### Edge Cases
- Creating task with duplicate number
- Editing task file corrupted during edit
- Renaming to existing ID
- Show with non-existent task
- Edit with no $EDITOR set

## Migration Checklist

- [ ] Migrate `cmd_show()` to `modern/core/commands.py`
- [ ] Migrate `cmd_create()` with full validation logic
- [ ] Migrate `cmd_edit()` with editor integration
- [ ] Migrate `cmd_rename()` with reference updates
- [ ] Locate and migrate delete/recover functions
- [ ] Update `modern/core/cli.py` with all subcommands
- [ ] Migrate all helper functions
- [ ] Create comprehensive test suite
- [ ] Link code references to REF-13
- [ ] Update verification commands
- [ ] Test backward compatibility

## Estimated Effort

**Total: 5 SP** (REF-13)

Breakdown:
- Show command: 0.5 SP
- Create command: 2 SP (most complex)
- Edit command: 1 SP (editor integration)
- Rename command: 1 SP (reference updates)
- Delete/recover: 0.5 SP

## Dependencies & Blockers

**Dependencies**:
- ListView (already available)
- show_card() function (available in modern/views)

**Blockers**:
- None

**Nice to have**:
- Editor validation/linting during edit
- Preview mode for create command
- Batch operations for rename
