# Core Module Migration Reference

## Overview
Complete migration of core task CRUD commands from `legacy/commands.py` to `modern/core/` module.

**Status**: ✅ COMPLETE (100%) - All commands migrated and reorganized

**Tracking Task**: REF-13

**Related Tasks**: REF-10 (Large features migration)

**Priority**: HIGH - Core commands are most frequently used

## ⚠️ IMPORTANT: Module Organization

**DO NOT create another mega commands.py file!**

The legacy `commands.py` is 2832 lines - this is an anti-pattern we're trying to avoid.

### Target Structure:
```
modern/core/
  __init__.py       # Exports all commands for easy imports
  cli.py            # CLI registration, imports from submodules
  read.py           # cmd_list, cmd_show (~175 lines)
  create.py         # cmd_create (~160 lines)
  edit.py           # cmd_edit (~20 lines)
  rename.py         # cmd_rename (~90 lines)
  delete.py         # cmd_delete, cmd_recover (TBD)
```

### Why Split Modules?
- **Maintainability**: Each operation is self-contained
- **Clarity**: Clear separation of concerns
- **Testability**: Easier to test individual operations
- **Reviewability**: Smaller files are easier to review
- **Avoids mega-files**: Prevents the 2832-line anti-pattern

### ✅ Resolution (2025-11-17):
- Successfully reorganized into 6 clean modules (695 lines total)
- All 5 commands migrated: list, show, create, edit, rename
- Phase 5 (REF-13e) reorganization: COMPLETE
- delete/recover removed from scope (don't exist in legacy)

## Legacy Code Locations

All core commands in: `src/taskpy/legacy/commands.py`

### Main Functions

| Function | Lines | Description | Status |
|----------|-------|-------------|--------|
| `cmd_create(args)` | 260-417 | Create new task | ✅ Migrated → `create.py` (175 lines) |
| `cmd_list(args)` | 418-475 | List tasks with filters | ✅ Migrated → `read.py` (88 lines) |
| `cmd_show(args)` | 477-552 | Display task details | ✅ Migrated → `read.py` (99 lines) |
| `cmd_edit(args)` | 553-570 | Edit task in $EDITOR | ✅ Migrated → `edit.py` (34 lines) |
| `cmd_rename(args)` | 2748-2832 | Rename task ID | ✅ Migrated → `rename.py` (103 lines) |

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

### Phase 1: Read Operations (REF-13a) - 0.5 SP ✅ COMPLETE
- [x] `list` command - DONE (FEAT-54) → `read.py`
- [x] `show` command - Display task card(s) → `read.py`
  - Single task: use `show_card()` from modern/views
  - Multiple tasks: loop and display each
  - Support both DATA and PRETTY modes

### Phase 2: Create Operation (REF-13b) - 2 SP ✅ COMPLETE
- [x] Migrate `cmd_create()` → `create.py` (175 lines)
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

### ~~Phase 4: Delete/Recover Operations (REF-13d)~~ - REMOVED
- Delete/recover commands DO NOT EXIST in legacy
- Confirmed by searching entire legacy/commands.py
- Removed from REF-13 scope

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

- [x] Migrate `cmd_show()` → `read.py` ✅
- [x] Migrate `cmd_create()` → `create.py` ✅
- [x] Migrate `cmd_edit()` → `edit.py` ✅
- [x] Migrate `cmd_rename()` → `rename.py` ✅
- [x] ~~Locate and migrate delete/recover~~ (don't exist) ✅
- [x] Update `modern/core/cli.py` with all subcommands ✅
- [x] Split into organized modules (avoid mega-file) ✅
- [x] Link code references to REF-13 ✅
- [ ] Create comprehensive test suite - **REMAINING**
- [ ] NFR compliance verification - **REMAINING**
- [x] Test backward compatibility ✅

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
