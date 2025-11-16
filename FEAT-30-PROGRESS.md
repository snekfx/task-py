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

### ⏳ Phase 3: Resolve Command
- [ ] Add `resolve` command to CLI parser
- [ ] Implement `cmd_resolve()` in commands.py
- [ ] Validate task epic matches BUGS*, REG*, DEF* pattern
- [ ] Require `--resolution` and `--reason` flags
- [ ] Add resolution metadata to Task model
- [ ] Move task to done with resolution tracking
- [ ] Bypass code/test ref gates for non-fixed resolutions
- [ ] Add tests for resolve command

**Resolution Types**:
- `fixed` - Bug fixed with code (normal qa→done)
- `duplicate` - Duplicate of another issue
- `cannot_reproduce` - Unable to reproduce
- `wont_fix` - Working as intended
- `config_change` - Fixed via configuration only
- `docs_only` - Addressed with documentation

### ⏳ Phase 4: Resolution Metadata
- [ ] Add `resolution` field to Task model
- [ ] Add `resolution_reason` field to Task model
- [ ] Add `ResolutionType` enum
- [ ] Display resolution info in task card
- [ ] Add resolution filtering to list command

## Key Design Decisions

1. **Regression is a Branch State**: Not part of normal promotion flow, only accessible from QA demotions
2. **REGRESSION → QA Requires Verification**: Same gates as ACTIVE → QA to ensure fixes are tested
3. **ISSUES Section Format**: Bulleted list with timestamps for easy chronological tracking
4. **Code Block Detection**: _append_issue_to_task_file skips markdown code blocks when finding section
5. **Issue Append After Write**: Issues appended AFTER write_task_file to avoid being overwritten

## Testing Notes

- BUGS-02 successfully migrated from in_progress → active
- Regression workflow tested (promote/demote logic)
- Issue tracking tested (creates section, appends entries)
- Code block detection prevents matching examples in documentation

## Next Steps

Continue with Phase 3: Implement resolve command for bug-type tasks.
