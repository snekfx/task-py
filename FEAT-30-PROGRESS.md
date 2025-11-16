# FEAT-30 Implementation Progress

**Task**: Add resolve command for BUGS/REGRESSION tasks
**Story Points**: 3
**Status**: In Progress (Phases 1-2 Complete, 3-4 Pending)

## Completed Work

### ✅ Phase 1: Status Migration (Commit: 4bb0364)
- Renamed `IN_PROGRESS` → `ACTIVE` in TaskStatus enum
- Added `REGRESSION` status for QA failures
- Created `data/kanban/status/regression/` directory
- Migrated `data/kanban/status/in_progress/` → `active/`
- Updated all code references across codebase
- Updated CLI choices, workflow arrays, theme mappings

**Files Changed**:
- `src/taskpy/models.py` - TaskStatus enum
- `src/taskpy/cli.py` - CLI choices
- `src/taskpy/commands.py` - Workflow arrays, status lists
- `src/taskpy/output.py` - Theme mapping
- `src/taskpy/storage.py` - Directory paths

### ✅ Phase 2: Regression Workflow (Commits: db1c11f, d5ca08e)

**Part A - Workflow Logic**:
- QA demotions now go to REGRESSION (not back to ACTIVE)
- REGRESSION can promote → QA for re-review
- REGRESSION can demote → ACTIVE for major rework
- Added validation: REGRESSION → QA uses same gates as ACTIVE → QA
- Added informational messages for regression transitions

**Part B - Issue Tracking**:
- Added `--issue` flag to `taskpy link` command
- Implemented `_append_issue_to_task_file()` helper function
- Auto-creates `## ISSUES` section in task markdown
- Appends timestamped entries: `- **YYYY-MM-DD HH:MM:SS UTC** - description`
- Skips code blocks when searching for ISSUES section

**Files Changed**:
- `src/taskpy/commands.py`:
  - `cmd_promote()` - Added REGRESSION → QA special case
  - `cmd_demote()` - Added QA → REGRESSION and REGRESSION → ACTIVE
  - `validate_promotion()` - Added REGRESSION → QA validation
  - `cmd_link()` - Added --issue handling
  - `_append_issue_to_task_file()` - New helper function
- `src/taskpy/cli.py` - Added --issue argument to link_parser

**Usage Examples**:
```bash
# Regression workflow
taskpy demote FEAT-10          # qa → regression (QA failure)
taskpy link FEAT-10 --issue "Tests failing on edge case"
taskpy promote FEAT-10         # regression → qa (retry)

# Issue tracking
taskpy link TASK-ID --issue "Memory leak in cleanup"
```

## Pending Work

### ⏳ Phase 4: List Filtering (Optional Enhancement)
- [ ] Add `--resolution` filter to list command
- [ ] Filter tasks by resolution type in list output
- [ ] Show resolution summary in stats command

## Completed Work (Continued)

### ✅ Phase 3: Resolve Command (Commit: TBD)

**Part A - CLI and Model**:
- Added `resolve` command to CLI parser with required flags
- Added `ResolutionType` enum (fixed, duplicate, cannot_reproduce, wont_fix, config_change, docs_only)
- Added resolution fields to Task model (resolution, resolution_reason, duplicate_of)
- Updated to_frontmatter_dict() to serialize resolution enum to string
- Updated read_task_file() to parse resolution fields from YAML

**Part B - Command Implementation**:
- Implemented `cmd_resolve()` in commands.py
- Validates task epic matches BUGS*, REG*, DEF* pattern (regex)
- Requires --resolution and --reason flags
- Optional --duplicate-of flag for duplicate resolutions
- Moves task directly to done with resolution tracking
- Bypasses normal QA gates for non-fixed resolutions
- Deletes old task file when status changes
- Displays resolution info with warning for bypassed gates

**Part C - Display**:
- Updated `cmd_show()` to display resolution metadata in data mode
- Shows resolution type, reason, and duplicate_of (if present)

**Files Changed**:
- `src/taskpy/cli.py` - Added resolve command parser
- `src/taskpy/models.py` - Added ResolutionType enum and resolution fields to Task
- `src/taskpy/commands.py` - Implemented cmd_resolve()
- `src/taskpy/storage.py` - Updated write/read for resolution fields

**Testing**:
- Tested `cannot_reproduce` resolution on BUGS-03
- Tested `duplicate` resolution with --duplicate-of on BUGS-04
- Verified feature tasks are rejected (FEAT-30)
- Verified resolution metadata persists in YAML frontmatter
- Verified resolution displays correctly in task show

**Resolution Types**:
- `fixed` - Bug fixed with code (normal qa→done)
- `duplicate` - Duplicate of another issue (requires --duplicate-of)
- `cannot_reproduce` - Unable to reproduce
- `wont_fix` - Working as intended
- `config_change` - Fixed via configuration only
- `docs_only` - Addressed with documentation

**Usage Examples**:
```bash
# Resolve bug that can't be reproduced
taskpy resolve BUGS-03 --resolution cannot_reproduce --reason "Unable to reproduce on latest version"

# Resolve duplicate bug
taskpy resolve BUGS-04 --resolution duplicate --duplicate-of BUGS-01 --reason "Same issue as BUGS-01"

# Resolve with docs only
taskpy resolve REG-05 --resolution docs_only --reason "Added troubleshooting guide to docs"

# Won't fix
taskpy resolve DEF-10 --resolution wont_fix --reason "Working as intended per spec"
```

## Key Design Decisions

1. **Regression is a Branch State**: Not part of normal promotion flow, only accessible from QA demotions
2. **REGRESSION → QA Requires Verification**: Same gates as ACTIVE → QA to ensure fixes are tested
3. **ISSUES Section Format**: Bulleted list with timestamps for easy chronological tracking
4. **Code Block Detection**: _append_issue_to_task_file skips markdown code blocks when finding section
5. **Issue Append After Write**: Issues appended AFTER write_task_file to avoid being overwritten
6. **Bug-Only Resolve**: Resolve command restricted to BUGS*/REG*/DEF* epics using regex validation
7. **Enum Serialization**: ResolutionType enum converted to string in YAML, parsed back to enum on read
8. **File Cleanup**: Old task file deleted when status changes to prevent duplicates

## Testing Notes

- BUGS-02 successfully migrated from in_progress → active
- Regression workflow tested (promote/demote logic)
- Issue tracking tested (creates section, appends entries)
- Code block detection prevents matching examples in documentation
- Resolve command tested with cannot_reproduce (BUGS-03)
- Resolve command tested with duplicate + --duplicate-of (BUGS-04)
- Feature task rejection verified (FEAT-30 rejected)
- Resolution metadata persists correctly in YAML frontmatter
- Resolution displays in task show --view data

## Next Steps

Phase 3 (Resolve Command) is complete! Optional Phase 4 would add resolution filtering to list/stats commands, but core functionality is fully implemented and tested.
