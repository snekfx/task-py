# Module Migration Summary & Quick Reference

## Migration Status Overview

| Module | Tracking Task | SP | Status | Lines in Legacy | Migrated | Reference Doc |
|--------|--------------|----|---------|----|----------|---------------|
| **Core** | REF-13 | 5 | 🟡 Partial (list only) | ~600 | list: 88 lines | [core-module-migration.md](./core-module-migration.md) |
| **Sprint** | REF-12 | 3 | 🟡 Partial (list only) | ~500 | list: 77 lines | [sprint-module-migration.md](./sprint-module-migration.md) |
| **Workflow** | REF-14 | 3 | 🔴 Not started | ~400 | 3 lines (stub) | (create doc) |
| **Display** | REF-15 | 3 | 🔴 Not started | ~300 | 3 lines (stub) | (create doc) |
| **Admin** | REF-16 | 3 | 🔴 Not started | ~400 | 3 lines (stub) | (create doc) |
| **Epics** | ✅ FEAT-56 | 2 | ✅ Complete | ~100 | 57 lines | N/A (done) |
| **NFRs** | ✅ REF-07 | - | ✅ Complete | ~100 | 28 lines | N/A (done) |
| **Milestones** | REF-17 | 2 | 🔴 Not started | ~200 | 3 lines (stub) | (create doc) |
| **Blocking** | (defer) | - | 🔴 Not started | ~200 | 3 lines (stub) | (may defer) |

**Legend**:
- 🟢 Complete - Fully migrated
- 🟡 Partial - Some commands migrated
- 🔴 Not started - Only stub exists

## Quick Command Location Reference

### Core Commands (REF-13)
```
src/taskpy/legacy/commands.py:
  cmd_create()   → lines 260-417   (❌ not migrated)
  cmd_list()     → lines 418-475   (✅ migrated to modern/core)
  cmd_show()     → lines 477-552   (❌ not migrated)
  cmd_edit()     → lines 553-570   (❌ not migrated)
  cmd_rename()   → lines 2748-2832 (❌ not migrated)
```

### Sprint Commands (REF-12)
```
src/taskpy/legacy/commands.py:
  cmd_sprint()            → line 1389 (router)
  _cmd_sprint_add()       → lines 1414-1445 (❌ not migrated)
  _cmd_sprint_remove()    → lines 1446-1477 (❌ not migrated)
  _cmd_sprint_list()      → lines 1478-1515 (✅ migrated to modern/sprint)
  _cmd_sprint_clear()     → lines 1516-1544 (❌ not migrated)
  _cmd_sprint_stats()     → lines 1545-1599 (❌ not migrated)
  _cmd_sprint_dashboard() → lines 1677-1791 (❌ not migrated)
  _cmd_sprint_recommend() → lines 1792-1850 (❌ not migrated)
  _cmd_sprint_init()      → lines 1632-1676 (❌ not migrated)
```

### Workflow Commands (REF-14)
```
src/taskpy/legacy/commands.py:
  cmd_promote()  → lines 571-643  (❌ not migrated)
  cmd_demote()   → lines 644-726  (❌ not migrated)
  cmd_move()     → lines 727-799  (❌ not migrated)
  cmd_block()    → TBD (locate in file)
  cmd_unblock()  → TBD (locate in file)
```

### Display Commands (REF-15)
```
src/taskpy/legacy/commands.py:
  cmd_info()      → lines 800-845  (❌ not migrated)
  cmd_stoplight() → lines 846-900  (❌ not migrated)
  cmd_kanban()    → lines 901-935  (❌ not migrated)
  cmd_history()   → lines 1196-1305 (❌ not migrated)
  cmd_stats()     → TBD (locate in file)
```

### Admin Commands (REF-16)
```
src/taskpy/legacy/commands.py:
  cmd_init()     → lines 220-259  (❌ not migrated)
  cmd_verify()   → lines 936-995  (❌ not migrated)
  cmd_session()  → lines 1377-1382 (❌ not migrated)
  cmd_groom()    → TBD (locate in file)
  cmd_manifest() → TBD (locate in file)
```

### Milestones Commands (REF-17)
```
src/taskpy/legacy/commands.py:
  cmd_milestones() → TBD (locate in file)
  cmd_milestone()  → TBD (locate in file)
```

## Migration Approach

### Pattern for All Modules

1. **Read legacy code** - Understand command logic and dependencies
2. **Create modern/MODULE/commands.py** - Implement command functions
3. **Update modern/MODULE/cli.py** - Add CLI registration
4. **Use modern views** - Integrate ListView, show_card, etc.
5. **Test** - Verify commands work via `taskpy modern MODULE cmd`
6. **Verify legacy unchanged** - Ensure `taskpy MODULE cmd` still works

### Common Dependencies

All commands will need:
- `TaskStorage` from `legacy/storage`
- Output utilities from `legacy/output`
- Modern views from `modern/views` (ListView, show_card, rolo_table)
- Legacy helpers from `legacy/commands` (during transition)

### Testing Strategy

For each module:
1. Unit tests for each command
2. Integration test for command workflow
3. Backward compatibility test (legacy still works)
4. Output mode test (PRETTY/DATA/AGENT)

## Next Steps

### Immediate (High Priority)
1. **REF-13** - Complete core module (create/show/edit/rename) - 5 SP
2. **BUGS-09** - Fix `taskpy link --doc` flag - 1 SP

### Medium Term
3. **REF-12** - Complete sprint module (add/remove/stats/dashboard) - 3 SP
4. **REF-14** - Complete workflow module (promote/demote/move) - 3 SP

### Lower Priority
5. **REF-15** - Complete display module (kanban/stats/history/info) - 3 SP
6. **REF-16** - Complete admin module (init/groom/manifest/verify) - 3 SP
7. **REF-17** - Complete milestones module - 2 SP

## Legacy Code Preservation

**Important**: `src/taskpy/legacy/commands.py` should remain unchanged until:
1. All modern modules are complete
2. All commands verified working in modern namespace
3. Comprehensive test coverage in place
4. Backward compatibility layer created

Only then consider removing legacy code (REF-04, REF-11).

## Reference Documents

- [Feature Module Architecture Plan](./feature-module-architecture.md) - Overall design
- [Core Module Migration](./core-module-migration.md) - Detailed core command migration
- [Sprint Module Migration](./sprint-module-migration.md) - Detailed sprint command migration

## Tracking Tasks

- **REF-04**: Break up mega files (parent tracking task)
- **REF-08**: Small features migration (NFRs ✅, Epics ✅, Milestones ❌)
- **REF-09**: Medium features migration (Sprint 🟡, Workflow ❌, Blocking ❌)
- **REF-10**: Large features migration (Core 🟡, Admin ❌, Display ❌)
- **REF-11**: Shared utilities extraction and legacy removal
- **REF-12**: Complete sprint module
- **REF-13**: Complete core module
- **REF-14**: Complete workflow module
- **REF-15**: Complete display module
- **REF-16**: Complete admin module
- **REF-17**: Complete milestones module
