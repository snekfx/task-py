# TaskPy Session Notes

## Critical Context for Continuation

### What's Working (Deployed)
- TaskPy v0.1.0-dev deployed to `/home/xnull/.local/bin/snek/taskpy`
- 51 tests passing (45 original + 6 sprint tests)
- Core workflow fully functional

### FEAT-09 Status (In Progress - 70% Complete)
**Completed:**
- ✅ Gate validation functions (commands.py:30-150)
- ✅ cmd_promote updated with gate checks (commands.py:386-436)
- ✅ --commit flag for promote (cli.py:199-202)
- ✅ Tested working gates (stub→backlog, in_progress→qa, qa→done)

**Gates enforce:**
- stub→backlog: needs description (20+ chars) + story points
- in_progress→qa: needs code refs, test refs, passing verification
- qa→done: needs commit hash

**Still TODO:**
1. `cmd_demote(args)` - move task backwards with --reason flag
2. `cmd_info(args)` - show current gate requirements for task
3. `cmd_stoplight(args)` - exit code validation (0=ready, 1=missing, 2=blocked)
4. Update `cmd_create()` to show file path in output
5. Add CLI parsers for demote/info/stoplight
6. Integration tests for gating
7. Promote FEAT-09 to done

### Key Files Modified
- `src/taskpy/models.py` - Added commit_hash, demotion_reason fields
- `src/taskpy/storage.py` - Updated for new fields, manifest columns
- `src/taskpy/commands.py` - Gate validators, updated cmd_promote
- `src/taskpy/cli.py` - Added --commit flag to promote

### Recent Tasks
- FEAT-14: Sprint selection (DONE)
- FEAT-21: Project type detection (BACKLOG, milestone-2, 5 SP)
- Tour command added (standalone feature)

### Next Actions
1. Finish FEAT-09 remaining commands (demote, info, stoplight)
2. OR pause and help migrate tasks
3. Consider FEAT-21 high priority (multi-lang workflow improvement)

### Token Usage
~127K/200K used this session
