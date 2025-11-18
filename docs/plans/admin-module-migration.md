# Admin Module Migration Reference

## Overview
Complete migration of admin/maintenance commands from `legacy/commands.py` to `modern/admin/` module.

**Status**: Not started (stub only)

**Tracking Task**: REF-16

**Related Tasks**: REF-10 (Large features migration)

**Priority**: MEDIUM - Admin commands are important for maintenance but less frequently used

## Legacy Code Locations

All admin commands in: `src/taskpy/legacy/commands.py`

### Main Functions

| Function | Lines | Description | Status |
|----------|-------|-------------|--------|
| `cmd_init(args)` | 220-259 | Initialize TaskPy structure | ❌ Not migrated |
| `cmd_verify(args)` | 936-995 | Run verification tests | ❌ Not migrated |
| `cmd_session(args)` | 1377-1382 | Manage work sessions (stub) | ❌ Not migrated |
| `cmd_groom(args)` | 2376-2414+ | Audit stub tasks for detail | ❌ Not migrated |
| `cmd_manifest(args)` | 2335-2374 | Manage manifest operations | ❌ Not migrated |

### Helper Functions

| Function | Purpose |
|----------|---------|
| `_cmd_manifest_rebuild(args)` | Rebuild manifest.tsv from task files |
| `_collect_status_tasks(storage, statuses)` | Collect tasks by status for groom |
| `storage.initialize(force, project_type)` | Initialize kanban structure |
| `storage.rebuild_manifest()` | Rebuild manifest index |
| `storage.run_verification_tests(task)` | Run verification for task |

## Dependencies

**Internal dependencies**:
- `TaskStorage` - all storage operations
- `StorageError` - error handling
- `print_success/error/info/warning` - output utilities
- Modern views for better display

**External tools**:
- Git integration (verify command may check git status)
- TOML config files (epics.toml, nfrs.toml, config.toml)

## Command API Structure

### Current Legacy API
```bash
taskpy init [--force] [--type TYPE]              # Initialize kanban structure
taskpy verify TASK-ID                            # Run verification tests
taskpy session                                   # Manage work sessions (stub)
taskpy groom [--ratio R] [--min-chars N]        # Audit stub task detail
taskpy manifest rebuild                          # Rebuild manifest index
```

### Target Modern API
```bash
taskpy modern init [--force] [--type TYPE]
taskpy modern verify TASK-ID
taskpy modern session
taskpy modern groom [--ratio R] [--min-chars N]
taskpy modern manifest rebuild
```

## Migration Tasks

### Phase 1: Initialization (REF-16a) - 1 SP
- [ ] Migrate `cmd_init()` - Project initialization
  - Create directory structure (data/kanban/info, status)
  - Create config files (config.toml, epics.toml, nfrs.toml)
  - Create manifest.tsv
  - Update .gitignore
  - Auto-detect project type (Rust, Python, Node, etc.)
  - Support --force flag for re-initialization
  - Support --type flag for explicit project type

### Phase 2: Maintenance Operations (REF-16b) - 1 SP
- [ ] Migrate `cmd_manifest()` - Manifest management
  - Router for manifest subcommands
  - _cmd_manifest_rebuild() - Rebuild index
- [ ] Migrate `cmd_verify()` - Verification tests
  - Load task
  - Run verification tests (storage.run_verification_tests)
  - Display results
- [ ] Migrate `cmd_groom()` - Stub task auditing
  - Calculate done task median length
  - Find stub tasks below threshold
  - Report tasks needing more detail

### Phase 3: Session Management (REF-16c) - 0.5 SP
- [ ] Implement `cmd_session()` - Work session tracking
  - Currently stub: "Session management coming soon"
  - Design session data structure
  - Session start/stop/status commands
  - Time tracking integration
  - Session summary reporting

### Phase 4: Testing & Integration (REF-16d) - 0.5 SP
- [ ] Create tests for each admin command
- [ ] Test init with various project types
- [ ] Test manifest rebuild with corrupt data
- [ ] Verify legacy commands still work
- [ ] Integration tests

## Key Implementation Notes

### Init Command Pattern
```python
# From legacy cmd_init (lines 220-259)
# 1. Get project type (explicit --type or auto-detect)
# 2. Call storage.initialize(force, project_type)
# 3. storage.initialize() creates:
#    - data/kanban/info/ directory
#    - data/kanban/status/ subdirectories (stub, backlog, ready, etc.)
#    - data/kanban/info/config.toml
#    - data/kanban/info/epics.toml
#    - data/kanban/info/nfrs.toml
#    - data/kanban/manifest.tsv
#    - Updates .gitignore
# 4. Print success with next steps
# 5. Handle StorageError if already initialized without --force
```

### Manifest Rebuild Pattern
```python
# From legacy cmd_manifest (lines 2335-2374)
# 1. Router pattern: cmd_manifest() dispatches to subcommands
# 2. _cmd_manifest_rebuild():
#    - Call storage.rebuild_manifest()
#    - storage scans all task files in status directories
#    - Rebuilds manifest.tsv index
#    - Returns count of indexed tasks
# 3. Print success with count and path
```

### Verify Command Pattern
```python
# From legacy cmd_verify (lines 936-995)
# 1. Find task file
# 2. Load task
# 3. Call storage.run_verification_tests(task)
# 4. Display verification results:
#    - Test name
#    - Status (pass/fail)
#    - Details/errors
# 5. Exit code based on results
```

### Groom Command Pattern
```python
# From legacy cmd_groom (lines 2376-2414+)
# Audit stub tasks for sufficient detail:
# 1. Collect all done/archived tasks
# 2. Calculate median task length (chars)
# 3. Calculate threshold: max(median * ratio, min_chars)
#    - Default ratio: 0.5 (stub should be 50% of done median)
#    - Default min_chars: 200
# 4. Collect all stub tasks
# 5. Find stub tasks below threshold
# 6. Report:
#    - Stub count
#    - Done median
#    - Threshold
#    - Tasks needing more detail
```

### Session Command Pattern
```python
# From legacy cmd_session (lines 1377-1382)
# Currently stub - needs implementation:
# Proposed design:
# - session start [TASK-ID] - Start work session
# - session stop - Stop current session
# - session status - Show current session
# - session list - Show recent sessions
# - session report - Generate time report
#
# Data structure:
# {
#   "session_id": "uuid",
#   "task_id": "FEAT-01",
#   "start_time": "2025-11-17T10:00:00Z",
#   "end_time": null,  # null if active
#   "duration": 3600,  # seconds
#   "notes": "optional notes"
# }
```

## Data Structures

### Config File (config.toml)
```toml
project_name = "MyProject"
project_type = "python"  # auto-detected or explicit
created = "2025-11-17T00:00:00Z"

[kanban]
statuses = ["stub", "backlog", "ready", "active", "qa", "done", "regression", "blocked"]
```

### Manifest Index (manifest.tsv)
```tsv
id	title	epic	status	story_points	priority	created	updated	in_sprint	milestone
FEAT-01	Feature title	FEAT	active	5	high	2025-11-17	2025-11-18	True	M1
```

### Verification Results
```python
{
  "task_id": "FEAT-01",
  "tests": [
    {
      "name": "acceptance_criteria",
      "status": "pass",
      "details": "All criteria defined"
    },
    {
      "name": "nfr_compliance",
      "status": "fail",
      "details": "Missing NFR-SEC-001"
    }
  ]
}
```

## Testing Strategy

### Unit Tests
- Test init with different project types
- Test init --force behavior
- Test manifest rebuild with various data
- Test verify with passing/failing tests
- Test groom with different thresholds
- Test session commands (when implemented)

### Integration Tests
- Full initialization workflow
- Manifest corruption and recovery
- Verification across task lifecycle
- Groom reporting accuracy

### Edge Cases
- Init in already initialized directory
- Init with invalid project type
- Manifest rebuild with corrupt task files
- Verify with non-existent task
- Groom with no done tasks
- Session start when session already active

## Migration Checklist

- [ ] Create `modern/admin/` module directory
- [ ] Migrate `cmd_init()` to `modern/admin/commands.py`
- [ ] Migrate `cmd_manifest()` with subcommand router
- [ ] Migrate `cmd_verify()` with test execution
- [ ] Migrate `cmd_groom()` with auditing logic
- [ ] Implement `cmd_session()` (currently stub)
- [ ] Create `modern/admin/cli.py` with command registration
- [ ] Update `modern/cli.py` to register admin module
- [ ] Create comprehensive test suite
- [ ] Link code references to REF-16
- [ ] Update verification commands
- [ ] Test backward compatibility

## Estimated Effort

**Total: 3 SP** (REF-16)

Breakdown:
- Initialization: 1 SP
- Maintenance operations (manifest/verify/groom): 1 SP
- Session management implementation: 0.5 SP
- Testing & integration: 0.5 SP

## Dependencies & Blockers

**Dependencies**:
- TaskStorage initialization logic (already in legacy)
- TOML config file templates
- Verification test framework (already in storage)

**Blockers**:
- None

**Nice to have**:
- Session time tracking with Pomodoro integration
- Groom auto-fix (expand stub tasks via AI)
- Init templates for different project types
- Verify integration with CI/CD
- Manifest export to JSON/CSV
