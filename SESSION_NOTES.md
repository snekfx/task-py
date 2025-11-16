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

### Key Files Modified
- `src/taskpy/models.py` - commit_hash, demotion_reason, blocked_reason fields
- `src/taskpy/storage.py` - Updated for new fields
- `src/taskpy/commands.py` - Gates + override + blocking logic
- `src/taskpy/cli.py` - Parsers for block/unblock commands
- `src/taskpy/output.py` - rolo_table implementation
- `tests/integration/test_cli.py` - 17 new tests (10 gating + 3 override + 4 blocking)

### Milestone-1 Progress
- **6/12 tasks done (50%), 23/33 SP complete (70%)**
- Done: FEAT-09, FEAT-10, FEAT-22, REF-02, FEAT-12, FEAT-02
- Stub: 6 tasks need grooming (DOCS-02, FEAT-04, FEAT-07, REF-01, FEAT-03, QOL-01)

### Next Actions (Milestone-1)
1. Groom stub tasks to move them to backlog
2. Consider tackling high-priority stub tasks (DOCS-02, FEAT-07, QOL-01)
3. Continue milestone-1 tasks to reach completion

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

### Token Usage
~85K/200K used this session (42%)
