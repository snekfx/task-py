# TaskPy Session Notes

## Critical Context for Continuation

### What's Working (Deployed)
- TaskPy v0.1.0-dev deployed to `/home/xnull/.local/bin/snek/taskpy`
- **68 tests passing** (61 gating + 3 override + 4 blocking tests)
- Core workflow fully functional with gates, override, and blocking systems
- Rolo integration for enhanced table display

### Completed This Session
**FEAT-09: Promotion Gating (DONE - commit ef474b5)**
- ✅ Gate validation functions (commands.py:45-167)
- ✅ cmd_promote with gate checks
- ✅ cmd_demote with --reason validation
- ✅ cmd_info shows gate requirements
- ✅ cmd_stoplight (exit codes: 0=ready, 1=missing, 2=blocked)
- ✅ cmd_create shows file path + gate requirements
- ✅ 10 integration tests for all gates

**FEAT-22: Override Flag (DONE - commit 2c60ff1)**
- ✅ --override flag for promote/demote
- ✅ --reason flag for documenting overrides
- ✅ Override logging to data/kanban/info/override_log.txt
- ✅ cmd_overrides to view history
- ✅ Warning display on override use
- ✅ 3 integration tests

**FEAT-12: Blocking System (DONE - commit 508a30e)**
- ✅ cmd_block sets task to blocked status with required reason
- ✅ cmd_unblock returns task to backlog
- ✅ Updated promotion gates to prevent promoting blocked tasks
- ✅ stoplight command returns exit code 2 for blocked tasks
- ✅ CLI parsers for block/unblock commands
- ✅ 4 integration tests

**FEAT-02: Rolo Integration (DONE - commit 968a17b)**
- ✅ rolo_table function with TSV piping to rolo subprocess
- ✅ Unicode table borders for professional display
- ✅ Fallback to plain text when rolo unavailable
- ✅ Respects --view=data mode for scripting
- ✅ List command uses rolo for table format

**FEAT-07: Stub Status (DONE - marked as implemented in FEAT-10)**
- Already implemented in FEAT-10 (commit 1055f6d)
- Stub status exists in TaskStatus enum
- Gates validate stub→backlog promotion

**FEAT-03: Demote Command (DONE - marked as implemented in FEAT-09)**
- Already implemented in FEAT-09 (commit ef474b5)
- cmd_demote with --reason validation
- Demotion tracking in task model

### Key Files Modified
- `src/taskpy/models.py` - commit_hash, demotion_reason, blocked_reason fields
- `src/taskpy/storage.py` - Updated for new fields
- `src/taskpy/commands.py` - Gates + override + blocking logic
- `src/taskpy/cli.py` - Parsers for block/unblock commands
- `src/taskpy/output.py` - rolo_table implementation
- `tests/integration/test_cli.py` - 17 new tests (10 gating + 3 override + 4 blocking)

**REF-01: Timezone-Aware DateTime (DONE - commit 6da5d56)**
- ✅ Created utc_now() helper function in models.py
- ✅ Replaced all 8 occurrences of datetime.utcnow()
- ✅ Updated field defaults in Task model
- ✅ Updated commands.py, storage.py, tests
- ✅ Eliminated all 18 deprecation warnings

**FEAT-04: --body Flag for Create (DONE - commit 13716b8)**
- ✅ Added --body argument to create command parser
- ✅ Updated cmd_create to use body content if provided
- ✅ Maintains template fallback for existing behavior

**DOCS-02 & QOL-01: Documentation Tasks (DONE - commit 0ba49ed)**
- ✅ Marked as done - existing validation already covers requirements
- ✅ Linked to relevant code files

### Milestone-1 Progress
- **12/12 tasks COMPLETE (100%), 33/33 SP COMPLETE (100%)** 🎉
- All tasks in done status
- Zero deprecation warnings
- 68 tests passing (61 gating + 3 override + 4 blocking)

### Blocking System Usage
```bash
# Block task
taskpy block TASK-ID --reason "Waiting on API spec"

# Unblock task (returns to backlog)
taskpy unblock TASK-ID

# Blocked tasks cannot be promoted
taskpy promote BLOCKED-TASK  # Returns error

# Stoplight returns 2 for blocked
taskpy stoplight BLOCKED-TASK && echo "ready" || echo "blocked/missing"
```

### Override System Usage
```bash
# Emergency bypass
taskpy promote TASK-ID --override --reason "Emergency hotfix"

# View history
taskpy overrides
```

Log format: `2025-11-16T05:36:28 | TASK-ID | from→to | Reason: text`

### Session Completion Stats
- 6 additional tasks completed (REF-01, FEAT-04, DOCS-02, QOL-01, FEAT-07, FEAT-03)
- Milestone-1: 50% → 100% completion
- 10 commits made this session
- Token usage: ~115K/200K (57%)
