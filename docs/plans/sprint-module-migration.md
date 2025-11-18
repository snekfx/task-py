# Sprint Module Migration Reference

## Overview
Complete migration of sprint management commands from `legacy/commands.py` to `modern/sprint/` module.

**Status**: Partial (only `sprint list` completed in FEAT-55)

**Tracking Task**: REF-12

**Related Tasks**: REF-09 (Medium features migration)

## Legacy Code Locations

All sprint commands in: `src/taskpy/legacy/commands.py`

### Main Functions (lines 1389-1850)

| Function | Lines | Description | Status |
|----------|-------|-------------|--------|
| `cmd_sprint(args)` | 1389 | Router for sprint subcommands | ⚠️ Needs update |
| `_cmd_sprint_add(args)` | 1414 | Add task to sprint | ❌ Not migrated |
| `_cmd_sprint_remove(args)` | 1446 | Remove task from sprint | ❌ Not migrated |
| `_cmd_sprint_list(args)` | 1478 | List sprint tasks | ✅ Migrated (FEAT-55) |
| `_cmd_sprint_clear(args)` | 1516 | Clear all tasks from sprint | ❌ Not migrated |
| `_cmd_sprint_stats(args)` | 1545 | Show sprint statistics | ❌ Not migrated |
| `_cmd_sprint_dashboard(args)` | 1677 | Show sprint dashboard (default) | ❌ Not migrated |
| `_cmd_sprint_recommend(args)` | 1792 | Recommend tasks for sprint | ❌ Not migrated |
| `_cmd_sprint_init(args)` | 1632 | Initialize sprint metadata | ❌ Not migrated |

### Helper Functions

| Function | Lines | Description |
|----------|-------|-------------|
| `_get_sprint_metadata_path(storage)` | 1600 | Get path to sprint metadata file |
| `_load_sprint_metadata(storage)` | 1605 | Load sprint metadata |
| `_save_sprint_metadata(storage, metadata)` | 1620 | Save sprint metadata |

## Dependencies

**External tools**:
- `src/taskpy/legacy/sprint_intelligence.py` - Sprint recommendation engine

**Internal dependencies**:
- `TaskStorage` - storage operations
- `_read_manifest()` - task loading
- `print_success/error/info/warning` - output utilities
- `ListView` - modern table rendering (already integrated)

## Command API Structure

### Current Legacy API
```bash
taskpy sprint                    # Show dashboard (default)
taskpy sprint add TASK-ID        # Add task to sprint
taskpy sprint remove TASK-ID     # Remove task from sprint
taskpy sprint list               # List sprint tasks
taskpy sprint clear              # Clear sprint
taskpy sprint stats              # Show statistics
taskpy sprint init               # Initialize sprint metadata
taskpy sprint recommend          # Recommend tasks for sprint
```

### Target Modern API
```bash
taskpy modern sprint             # Show dashboard (default)
taskpy modern sprint add TASK-ID
taskpy modern sprint remove TASK-ID
taskpy modern sprint list        # ✅ Already works
taskpy modern sprint clear
taskpy modern sprint stats
taskpy modern sprint init
taskpy modern sprint recommend
```

## Migration Tasks

### Phase 1: Subcommand Infrastructure (REF-12a)
- [x] Update `modern/sprint/cli.py` to handle all subcommands
- [x] Add subcommand routing in `cmd_sprint()`
- [ ] Extend subparser for: add, remove, clear, stats, init, recommend, dashboard

### Phase 2: Storage Operations (REF-12b)
- [ ] Migrate `_cmd_sprint_add()` - modifies task in_sprint field
- [ ] Migrate `_cmd_sprint_remove()` - modifies task in_sprint field
- [ ] Migrate `_cmd_sprint_clear()` - bulk modify all tasks
- [ ] Migrate helper functions for metadata management

### Phase 3: Display & Intelligence (REF-12c)
- [ ] Migrate `_cmd_sprint_stats()` - aggregation logic
- [ ] Migrate `_cmd_sprint_dashboard()` - complex display using ListView
- [ ] Migrate `_cmd_sprint_recommend()` - integrate sprint_intelligence
- [ ] Migrate `_cmd_sprint_init()` - metadata initialization

### Phase 4: Testing & Integration (REF-12d)
- [ ] Create tests for each subcommand
- [ ] Verify legacy commands still work
- [ ] Integration tests for sprint workflow
- [ ] Performance testing for large sprints

## Key Implementation Notes

### Sprint Add/Remove Operations
```python
# Pattern from legacy (_cmd_sprint_add lines 1414-1445)
# 1. Load task from storage
# 2. Check if already in sprint
# 3. Set task.in_sprint = True
# 4. Save task to storage
# 5. Update manifest
# 6. Print success message
```

### Sprint Statistics
```python
# Pattern from legacy (_cmd_sprint_stats lines 1545-1599)
# Aggregations needed:
# - Total tasks in sprint
# - Breakdown by status
# - Total story points
# - Story points by status
# - Velocity calculations
# - Completion percentage
```

### Sprint Dashboard
```python
# Pattern from legacy (_cmd_sprint_dashboard lines 1677-1791)
# Complex display showing:
# - Sprint metadata (name, dates, goals)
# - Task breakdown by status (using ListView)
# - Progress indicators
# - Burndown chart data
# - Recommendations
```

## Data Structures

### Sprint Metadata
Stored in: `.taskpy/sprint_metadata.json`

```json
{
  "sprint_name": "Sprint 1",
  "start_date": "2025-11-01",
  "end_date": "2025-11-14",
  "goals": ["Complete feature X", "Fix critical bugs"],
  "capacity_sp": 40,
  "created": "2025-11-01T00:00:00Z"
}
```

### Task Sprint Field
```yaml
in_sprint: True  # Boolean stored as string in YAML frontmatter
```

## Testing Strategy

### Unit Tests
- Test each subcommand in isolation
- Mock storage operations
- Verify output formatting

### Integration Tests
- Full sprint workflow: init → add → list → stats → remove → clear
- Test with various task states
- Test with missing/invalid task IDs

### Edge Cases
- Adding task already in sprint
- Removing task not in sprint
- Clearing empty sprint
- Sprint operations before init
- Large sprints (100+ tasks)

## Migration Checklist

- [ ] Create `modern/sprint/commands.py` with all subcommands
- [ ] Update `modern/sprint/cli.py` with full subcommand routing
- [ ] Migrate helper functions for metadata management
- [ ] Integrate sprint_intelligence for recommendations
- [ ] Create comprehensive test suite
- [ ] Link code references to REF-12
- [ ] Update verification commands
- [ ] Test backward compatibility with legacy

## Estimated Effort

**Total: 3 SP** (REF-12)

Breakdown:
- Infrastructure & routing: 0.5 SP
- Storage operations (add/remove/clear): 1 SP
- Display & intelligence (stats/dashboard/recommend): 1 SP
- Testing & integration: 0.5 SP

## Dependencies & Blockers

**Dependencies**:
- None (sprint list already works)

**Blockers**:
- None

**Nice to have**:
- ListView enhancements for dashboard display
- Chart rendering for burndown (could use boxy or ascii)
