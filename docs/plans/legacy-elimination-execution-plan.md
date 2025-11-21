# Legacy Elimination Execution Plan (2025-11-21)

## Executive Summary

**CRITICAL FINDING**: Previous migration efforts created modern modules that are NOT self-sufficient. They are thin wrappers that import and call legacy code. This document outlines the TRUE migration work required to eliminate all `taskpy.legacy.*` dependencies.

**Reality Check**:
- ✅ Only 1 module actually complete: REF-13 (Core)
- ❌ 8 tickets falsely marked complete, reopened to backlog (34 SP)
- 🚫 REF-11 (legacy removal) blocked until dependencies eliminated
- 📊 Found 50+ legacy imports across "modern" modules

---

## The Problem: What Went Wrong

### What Was SUPPOSED To Happen
1. Copy legacy Models → `modern/shared/models.py` or module-specific models
2. Copy legacy Storage → `modern/shared/tasks.py` or modern storage layer
3. Copy legacy Output → `modern/shared/messages.py` and `modern/shared/output.py`
4. Update modern module code to use new locations
5. **Eliminate ALL `from taskpy.legacy` imports**

### What ACTUALLY Happened
Modern modules were created that simply import from legacy:
```python
# modern/sprint/commands.py - WRONG!
from taskpy.legacy.storage import TaskStorage  # ❌ Still dependent!
from taskpy.legacy.models import Task, TaskStatus  # ❌ Still dependent!
from taskpy.legacy.output import print_success, print_error  # ❌ Still dependent!
```

This creates the **illusion** of migration while maintaining full dependency on legacy code.

### Why This Matters
- **Cannot remove legacy code** - modern modules will break
- **Not a true migration** - just moved files around
- **Blocks REF-11** - legacy removal impossible
- **Technical debt** - two systems doing the same thing

---

## Success Criteria: What "Complete" Actually Means

### Definition of Done (Per Module)

For a module migration to be **truly complete**:

1. ✅ **ZERO legacy imports**: `grep -r "from taskpy.legacy" src/taskpy/modern/MODULE/` returns NOTHING
2. ✅ All functionality works without legacy code
3. ✅ Tests pass and cover the migrated code
4. ✅ Modern equivalents exist for all used legacy components
5. ✅ Documentation updated

### Verification Command

For each module:
```bash
# This MUST return empty output for completion
grep -r "from taskpy.legacy" src/taskpy/modern/MODULE_NAME/ --include="*.py"

# Example for sprint module:
grep -r "from taskpy.legacy" src/taskpy/modern/sprint/ --include="*.py"
```

If ANY results appear, the migration is **incomplete**.

---

## Legacy Code Mapping: What Needs To Be Migrated

### Current Legacy Components Used by Modern Modules

| Legacy Component | Used By | Modern Equivalent | Status |
|-----------------|---------|-------------------|--------|
| `legacy.models.Task` | All modules | `modern/shared/models.py` | ⚠️ Partial |
| `legacy.models.TaskStatus` | All modules | `modern/shared/models.py` | ⚠️ Partial |
| `legacy.storage.TaskStorage` | All modules | `modern/shared/tasks.py` | ✅ Exists (core uses it) |
| `legacy.output.print_*` | All modules | `modern/shared/messages.py` | ✅ Exists (core uses it) |
| `legacy.output.OutputMode` | CLI, views | `modern/shared/output.py` | ✅ Exists |
| `legacy.commands._read_manifest` | display, milestones | `modern/shared/tasks.py` | ❌ Needs migration |
| `legacy.commands._sort_tasks` | display | `modern/shared/tasks.py` | ❌ Needs migration |

### Modules Still Using Legacy (in dependency order)

```
📦 modern/
├── ✅ core/          - CLEAN (no legacy imports)
├── ✅ views/         - CLEAN (no legacy imports)
├── ❌ nfrs/          - Uses: legacy.storage, legacy.output
├── ❌ epics/         - Uses: legacy.storage, legacy.output
├── ❌ milestones/    - Uses: legacy.storage, legacy.output, legacy.commands
├── ❌ sprint/        - Uses: legacy.storage
├── ❌ workflow/      - Uses: legacy.models, legacy.storage, legacy.output
├── ❌ display/       - Uses: legacy.models, legacy.storage, legacy.output, legacy.commands
├── ❌ admin/         - Uses: legacy.models, legacy.storage, legacy.output
├── ❌ blocking/      - Uses: legacy.models, legacy.storage, legacy.output
├── ❌ signoff/       - Uses: legacy.output, legacy.storage
├── ❌ archival/      - Uses: legacy.models, legacy.output, legacy.storage
├── ❌ tags/          - Uses: legacy.output, legacy.storage
├── ❌ search/        - Uses: legacy.output
├── ❌ flags/         - Uses: legacy.output, legacy.storage
└── ❌ linking/       - (need to check)
```

---

## Execution Plan: Step-by-Step Migration

### Phase 0: Prepare Foundation (0.5 SP)

**Goal**: Ensure modern/shared has everything needed

1. **Verify existing modern utilities**:
   ```bash
   ls -la src/taskpy/modern/shared/
   # Should have: models.py, tasks.py, messages.py, output.py, utils.py
   ```

2. **Check what's already migrated** (Core did this work):
   - ✅ `modern/shared/tasks.py` - has file operations, task reading
   - ✅ `modern/shared/messages.py` - has print_* functions
   - ✅ `modern/shared/output.py` - has OutputMode enum

3. **Identify missing pieces**:
   ```bash
   # Find what legacy.commands exports that we need
   grep "^def _" src/taskpy/legacy/commands.py | head -20
   # Need to migrate: _read_manifest, _sort_tasks
   ```

**Deliverable**: Document in `modern/shared/README.md` what's available

---

### Phase 1: Simple Modules (5 SP total)

Start with modules that have minimal dependencies.

#### 1.1 REF-17: Milestones Module (2 SP)

**Current State**: Uses `legacy.storage`, `legacy.output`, `legacy.commands`

**Migration Steps**:
1. Read `src/taskpy/modern/milestones/commands.py`
2. Replace `from taskpy.legacy.storage import TaskStorage` → use `modern/shared/tasks.py`
3. Replace `from taskpy.legacy.output import print_*` → use `modern/shared/messages.py`
4. Replace `from taskpy.legacy.commands import _read_manifest` → migrate to `modern/shared/tasks.py`
5. Test: `taskpy milestones` still works
6. Verify: `grep -r "from taskpy.legacy" src/taskpy/modern/milestones/` returns NOTHING

**Files to modify**:
- `src/taskpy/modern/milestones/commands.py`
- `src/taskpy/modern/shared/tasks.py` (add _read_manifest if needed)

**Reference**: See `docs/plans/milestones-module-migration.md`

---

#### 1.2 REF-08: NFRs/Epics Modules (3 SP)

**Current State**:
- `modern/nfrs/commands.py` uses `legacy.storage`, `legacy.output`
- `modern/epics/commands.py` uses `legacy.storage`, `legacy.output`

**Migration Steps (NFRs)**:
1. Read `src/taskpy/modern/nfrs/commands.py`
2. Replace storage calls with `modern/shared/tasks.py` functions
3. Replace output calls with `modern/shared/messages.py` functions
4. Test: `taskpy nfrs` works
5. Verify: No legacy imports remain

**Migration Steps (Epics)**:
1. Read `src/taskpy/modern/epics/commands.py`
2. Same replacements as NFRs
3. Test: `taskpy epics` works
4. Verify: No legacy imports remain

**Files to modify**:
- `src/taskpy/modern/nfrs/commands.py`
- `src/taskpy/modern/epics/commands.py`

---

### Phase 2: Medium Modules (12 SP total)

Modules with more complex dependencies.

#### 2.1 REF-12: Sprint Module (3 SP)

**Current State**: Uses `legacy.storage` extensively

**Migration Steps**:
1. Read `src/taskpy/modern/sprint/commands.py`
2. Identify all TaskStorage usages
3. Replace with `modern/shared/tasks.py` equivalents
4. If functions missing, add them to `modern/shared/tasks.py`
5. Test all sprint commands: add, remove, list, clear, stats, dashboard
6. Verify: No legacy imports

**Reference**: See `docs/plans/sprint-module-migration.md`

---

#### 2.2 REF-14: Workflow Module (3 SP)

**Current State**: Uses `legacy.models`, `legacy.storage`, `legacy.output`

**Migration Steps**:
1. Read `src/taskpy/modern/workflow/commands.py`
2. Replace Task, TaskStatus, HistoryEntry → use `modern/shared/models.py`
3. Replace storage operations → use `modern/shared/tasks.py`
4. Replace output functions → use `modern/shared/messages.py`
5. Test: promote, demote, move commands
6. Verify: No legacy imports

**Reference**: See `docs/plans/workflow-module-migration.md`

---

#### 2.3 REF-15: Display Module (3 SP)

**Current State**: Uses `legacy.models`, `legacy.storage`, `legacy.output`, `legacy.commands`

**Migration Steps**:
1. Read `src/taskpy/modern/display/commands.py`
2. Replace models with modern equivalents
3. Migrate `_read_manifest`, `_sort_tasks` to `modern/shared/tasks.py`
4. Replace storage and output imports
5. Test: kanban, stats, history, info, stoplight
6. Verify: No legacy imports

**Reference**: See `docs/plans/display-module-migration.md`

---

#### 2.4 REF-16: Admin Module (3 SP)

**Current State**: Uses `legacy.models`, `legacy.storage`, `legacy.output`

**Migration Steps**:
1. Read `src/taskpy/modern/admin/commands.py`
2. Replace all model imports
3. Replace storage operations
4. Replace output functions
5. Test: init, groom, manifest, verify, session
6. Verify: No legacy imports

**Reference**: See `docs/plans/admin-module-migration.md`

---

### Phase 3: Complex Multi-Module Tickets (10 SP total)

#### 3.1 REF-09: Sprint/Workflow/Blocking (5 SP)

**Note**: This is a TRACKING ticket covering multiple modules

**Migration Steps**:
1. Verify REF-12 (Sprint) is complete
2. Verify REF-14 (Workflow) is complete
3. Migrate Blocking module:
   - Read `src/taskpy/modern/blocking/commands.py`
   - Replace legacy imports
   - Test: block, unblock commands
   - Verify: No legacy imports
4. Close REF-09 once all three modules are clean

---

#### 3.2 REF-10: Core/Admin/Display (5 SP)

**Note**: This is a TRACKING ticket covering multiple modules

**Migration Steps**:
1. Verify REF-13 (Core) is already complete ✅
2. Verify REF-16 (Admin) is complete
3. Verify REF-15 (Display) is complete
4. Close REF-10 once all three modules are clean

---

### Phase 4: Additional Modules (Not tracked in REF tickets)

These modules also need cleanup but aren't in formal REF tickets:

- `modern/signoff/` - uses legacy
- `modern/archival/` - uses legacy
- `modern/tags/` - uses legacy
- `modern/search/` - uses legacy
- `modern/flags/` - uses legacy
- `modern/linking/` - uses legacy

**Recommendation**: Create tracking tickets for these or handle as technical debt cleanup.

---

### Phase 5: Final Verification & Legacy Removal (5 SP)

#### 5.1 REF-11: Legacy Removal (5 SP)

**BLOCKED UNTIL**: All REF-08, 09, 10, 12, 14, 15, 16, 17 complete

**Prerequisites**:
```bash
# This MUST return NOTHING
grep -r "from taskpy.legacy" src/taskpy/modern/ --include="*.py"
```

**Migration Steps**:
1. Run global verification command
2. Verify all tests pass
3. Audit command parity (legacy vs modern)
4. Create removal branch
5. Update entry points to use modern CLI directly
6. Remove legacy CLI files (commands.py, cli.py)
7. Keep legacy/models.py, legacy/storage.py temporarily (for reference)
8. Update all documentation
9. Run full test suite
10. Deploy and smoke test

**Reference**: See REF-11 ticket for detailed acceptance criteria

---

## Common Migration Patterns

### Pattern 1: Replace TaskStorage

**Before**:
```python
from taskpy.legacy.storage import TaskStorage

storage = TaskStorage()
task = storage.read_task(task_id)
storage.update_task(task)
```

**After**:
```python
from taskpy.modern.shared.tasks import read_task_file, write_task_file

task = read_task_file(task_id)
write_task_file(task)
```

---

### Pattern 2: Replace Models

**Before**:
```python
from taskpy.legacy.models import Task, TaskStatus, HistoryEntry

task = Task(...)
if task.status == TaskStatus.ACTIVE:
    ...
```

**After**:
```python
from taskpy.modern.shared.models import Task, TaskStatus, HistoryEntry

task = Task(...)
if task.status == TaskStatus.ACTIVE:
    ...
```

**Note**: If models don't exist yet, copy from legacy to modern/shared/models.py

---

### Pattern 3: Replace Output Functions

**Before**:
```python
from taskpy.legacy.output import print_success, print_error, print_info

print_success("Task created")
print_error("Task not found")
```

**After**:
```python
from taskpy.modern.shared.messages import print_success, print_error, print_info

print_success("Task created")
print_error("Task not found")
```

---

### Pattern 4: Replace Helper Functions

**Before**:
```python
from taskpy.legacy.commands import _read_manifest, _sort_tasks

manifest = _read_manifest()
sorted_tasks = _sort_tasks(tasks)
```

**After**:
```python
from taskpy.modern.shared.tasks import read_manifest, sort_tasks

manifest = read_manifest()
sorted_tasks = sort_tasks(tasks)
```

**Note**: Migrate helper functions to modern/shared/tasks.py first

---

## Verification Checklist

For each module migration:

- [ ] No `from taskpy.legacy` imports remain
- [ ] All commands work correctly
- [ ] Tests pass (unit and integration)
- [ ] Documentation updated
- [ ] Code references linked to ticket
- [ ] Commit hash recorded in ticket

Global verification (before REF-11):

- [ ] `grep -r "from taskpy.legacy" src/taskpy/modern/` returns NOTHING
- [ ] Full test suite passes
- [ ] All REF tickets (08, 09, 10, 12, 14, 15, 16, 17) marked done
- [ ] Command parity audit complete (modern == legacy functionality)

---

## Troubleshooting

### "But the tests pass!"

Tests passing doesn't mean migration is complete. If modern code still imports legacy, it's not truly migrated.

### "It's just a wrapper, why rewrite?"

Because the goal is to **remove legacy code entirely**. Wrappers maintain the dependency and block deletion.

### "Can't we keep models/storage in legacy?"

No. The whole point of REF-11 is to delete `src/taskpy/legacy/` directory. Modern must be self-sufficient.

### "This seems like a lot of work"

Yes. Real migration is more work than wrapping. That's why this document exists - to prevent future confusion about what "done" means.

---

## Timeline Estimate

| Phase | Work | Story Points | Time Estimate |
|-------|------|--------------|---------------|
| Phase 0 | Foundation prep | 0.5 SP | 1 day |
| Phase 1 | Simple modules (17, 08) | 5 SP | 1-2 weeks |
| Phase 2 | Medium modules (12, 14, 15, 16) | 12 SP | 3-4 weeks |
| Phase 3 | Complex tickets (09, 10) | 10 SP | 2-3 weeks |
| Phase 4 | Additional modules | TBD | TBD |
| Phase 5 | Legacy removal (11) | 5 SP | 1-2 weeks |
| **Total** | **Core migration** | **32.5 SP** | **8-12 weeks** |

**Note**: These are estimates. Actual time depends on:
- Discovery of hidden dependencies
- Test failures requiring debugging
- Need to migrate additional utility functions
- Code review and QA cycles

---

## Success Metrics

### Hard Requirements
- ✅ Zero legacy imports in modern modules
- ✅ All tests pass
- ✅ Full command parity with legacy

### Quality Metrics
- 📊 Test coverage maintained or improved
- 📈 Performance not degraded
- 📚 Documentation complete
- 🎯 No regressions reported

---

## Lessons Learned

### What NOT To Do
- ❌ Mark tickets "complete" when they just import legacy
- ❌ Create wrappers instead of true migrations
- ❌ Skip verification commands
- ❌ Rush through multiple modules without proper testing
- ❌ Ignore the "no legacy imports" requirement

### What TO Do
- ✅ Verify ZERO legacy imports before marking complete
- ✅ Copy code to modern equivalents, not just import it
- ✅ Test thoroughly after each module
- ✅ Update documentation as you go
- ✅ Use the verification commands
- ✅ One module at a time, properly

---

## References

- [Migration Audit 2025-11-17](./migration-audit-2025-11-17.md) - Comprehensive audit
- [Core Module Migration](./core-module-migration.md) - Example of CORRECT migration
- [Sprint Module Migration](./sprint-module-migration.md) - Sprint-specific guide
- [Workflow Module Migration](./workflow-module-migration.md) - Workflow-specific guide
- [Display Module Migration](./display-module-migration.md) - Display-specific guide
- [Admin Module Migration](./admin-module-migration.md) - Admin-specific guide
- [Milestones Module Migration](./milestones-module-migration.md) - Milestones-specific guide
- [Feature Module Architecture](./feature-module-architecture.md) - Overall design
- [Migration Summary](./migration-summary.md) - Quick reference

---

## Document History

- **2025-11-21**: Created after discovering that "completed" migration tickets still had legacy dependencies
- **Purpose**: Provide unambiguous execution plan for TRUE migration (not wrappers)
- **Audience**: Future developers (including Codex/AI agents) working on migration

---

## Questions?

If you're working on a migration ticket and unsure:

1. **Read this document fully**
2. **Check the module-specific migration guide** (docs/plans/)
3. **Verify with the command**: `grep -r "from taskpy.legacy" src/taskpy/modern/MODULE/`
4. **If it returns anything**: Migration is NOT complete
5. **If it returns nothing**: Proceed with testing

**Remember**: "Done" means ZERO legacy imports, not "wraps legacy and calls it."
