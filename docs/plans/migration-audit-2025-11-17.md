# Migration Audit Report - 2025-11-17

## Executive Summary

Auditing all 31 legacy commands against modern implementations to update REF tickets accurately.

## Legacy Commands Inventory (31 total)

```
220:cmd_init        → Admin (REF-16)
260:cmd_create      → Core (REF-13)  ✅ MIGRATED
418:cmd_list        → Core (REF-13)  ✅ MIGRATED
477:cmd_show        → Core (REF-13)  ✅ MIGRATED
565:cmd_edit        → Core (REF-13)  ✅ MIGRATED
583:cmd_promote     → Workflow (REF-14)
656:cmd_demote      → Workflow (REF-14)
739:cmd_move        → Workflow (REF-14)
812:cmd_info        → Display (REF-15)
858:cmd_stoplight   → Display (REF-15)
913:cmd_kanban      → Display (REF-15)
948:cmd_verify      → Admin (REF-16)
1008:cmd_epics      → Epics (REF-08) ✅ COMPLETE
1032:cmd_nfrs       → NFRs (REF-07) ✅ COMPLETE
1096:cmd_link       → Linking (BUGS-09 + future)
1150:cmd_issues     → ???
1208:cmd_history    → Display (REF-15)
1318:cmd_resolve    → ???
1389:cmd_session    → Admin (REF-16)
1395:cmd_tour       → Help (no migration planned)
1401:cmd_sprint     → Sprint (REF-12) ⚠️ PARTIAL
1917:cmd_stats      → Display (REF-15)
1970:cmd_overrides  → ???
2004:cmd_block      → Blocking (REF-09)
2036:cmd_unblock    → Blocking (REF-09)
2285:cmd_milestones → Milestones (REF-17)
2325:cmd_milestone  → Milestones (REF-17)
2347:cmd_manifest   → Admin (REF-16)
2388:cmd_groom      → Admin (REF-16)
2707:cmd_help       → Help (no migration planned)
2760:cmd_rename     → Core (REF-13) ✅ MIGRATED
```

## Module-by-Module Status

### ✅ Core (REF-13) - 4.5/5 SP Complete
**Modern files:** read.py (187), create.py (175), edit.py (34), rename.py (103)
**Migrated (5/6):**
- list ✅
- show ✅
- create ✅
- edit ✅
- rename ✅

**Missing (0.5 SP):**
- delete/recover - need to locate in legacy

**Status:** ACTIVE - Phase 5 (reorganization) DONE ✅

### ⚠️ Sprint (REF-12) - 1/7 commands (3 SP remaining)
**Modern file:** commands.py (77 lines)
**Migrated (1/7):**
- sprint list ✅

**Missing (3 SP):**
- sprint add
- sprint remove
- sprint clear
- sprint stats
- sprint dashboard
- sprint recommend
- sprint init

**Status:** STUB - Needs full migration

### ❌ Workflow (REF-14) - 0/3 commands (3 SP)
**Modern file:** commands.py (3 lines - stub)
**Missing:**
- promote
- demote
- move

**Status:** STUB - Not started

### ❌ Display (REF-15) - 0/5 commands (3 SP)
**Modern file:** commands.py (3 lines - stub)
**Missing:**
- info
- stoplight
- kanban
- stats
- history

**Status:** STUB - Not started

### ❌ Admin (REF-16) - 0/5 commands (3 SP)
**Modern file:** commands.py (3 lines - stub)
**Missing:**
- init
- verify
- session
- manifest (with rebuild subcommand)
- groom

**Status:** STUB - Not started

### ✅ Epics (REF-08) - COMPLETE
**Modern file:** commands.py (57 lines)
**Migrated:**
- epics (list) ✅

**Status:** DONE - Only one command exists

### ✅ NFRs (REF-07) - COMPLETE
**Modern file:** commands.py (28 lines)
**Migrated:**
- nfrs (list) ✅

**Status:** DONE - Only one command exists

### ❌ Milestones (REF-17) - 0/5 commands (2 SP)
**Modern file:** commands.py (3 lines - stub)
**Missing:**
- milestones (list)
- milestone show
- milestone start
- milestone complete
- milestone assign

**Status:** STUB - Not started, NOT even registered in modern CLI

### Commands NOT in REF Tickets
- cmd_link (BUGS-09 addresses --doc flag only)
- cmd_issues (line 1150)
- cmd_resolve (line 1318)
- cmd_overrides (line 1970)
- cmd_block/cmd_unblock (REF-09 mentions but no discrete task)
- cmd_tour (help command, no migration needed)
- cmd_help (help command, no migration needed)

## Priority Order for Completion

1. **REF-13** - Core delete/recover (0.5 SP) - HIGH
2. **BUGS-09** - Fix link --doc flag (1 SP) - HIGH
3. **REF-12** - Sprint module (3 SP) - MEDIUM
4. **REF-14** - Workflow module (3 SP) - MEDIUM  
5. **REF-15** - Display module (3 SP) - MEDIUM
6. **REF-16** - Admin module (3 SP) - MEDIUM
7. **REF-17** - Milestones module (2 SP) - LOW

## Total Remaining Work: 15.5 SP
