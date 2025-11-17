# HANDOFF – TaskPy Session (v0.2.3 sprint intelligence complete)

## Highlights
- ✅ **FEAT-37 COMPLETE**: Sprint intelligence system with smart dashboard and recommendations (commit: 89b1198)
  - `taskpy sprint` now shows intelligent dashboard (default, no subcommand needed)
  - Sprint metadata stored in `data/kanban/info/sprint_current.json`
  - Progress bar shows completed SP / capacity SP
  - Tasks grouped by status with emoji indicators (🔥 active, 🧪 qa, ✅ done, etc.)
  - Days remaining calculator and sprint completion detection
  - `taskpy sprint init` creates new sprints with title, focus, capacity, dates
  - `taskpy sprint recommend` intelligently suggests tasks based on capacity and priority
  - All legacy sprint commands still work (add, remove, list, clear, stats)

- ✅ **FEAT-13 COMPLETE**: Auto-incrementing sequence ID for chronological sorting (commit: 70758b6)
  - Global `auto_id` field on all tasks (separate from epic numbering)
  - Sequence counter in `data/kanban/.sequence`
  - `--sort` flag on list/kanban: priority (default), created, id, status
  - 62 existing tasks backfilled with auto_id based on creation timestamp

- ✅ **Help system improvements**: `taskpy help` and `taskpy --help` now identical (commits: 6417549, 7e94149)
  - Both show logo, version, and full command help
  - Custom HelpAction class for consistent output

- ✅ **List filtering fixed**: Done/archived tasks hidden by default unless `--all` or explicit status filter (commit: cfb324e)

- **Known Issue**: Task file serialization bug when linking files
  - Symptom: Task files occasionally get deleted/corrupted during link operations
  - Workaround: Keep backups of important task files before linking
  - Root cause: History entries storing dict objects instead of serialized strings

## Task Board State
- **Total**: 65 tasks, 194 story points
- **Done**: 32 tasks (including FEAT-37 and FEAT-13)
- **Stub**: 25 tasks
- **Backlog**: 8 tasks
- **Active**: 0 tasks (ready for next work)

**New stub tasks created:**
- QOL-12: Delete command (2 SP, medium)
- REF-03: Migrate overrides to history system (2 SP, medium)
- REF-04: Break up mega files and extract shared utilities (5 SP, medium)

## Next Suggested Work
1. **REF-04**: Break up mega files (5 SP, high priority)
   - `commands.py` is 2398 lines
   - Split into: core.py, workflow.py, sprint.py, admin.py
   - Extract shared utilities: gates.py, loading.py, formatting.py

2. **REF-03**: Migrate overrides to use task history system (2 SP)
   - Consolidate override_log.txt into HistoryEntry with action='override'

3. **Fix serialization bugs**: Investigate history entry dict storage issue

4. **FEAT-36**: Sprint complete workflow (3 SP) - now unblocked with FEAT-37 done
   - Archive completed sprints, velocity metrics, summary generation

5. Wire groom thresholds into promotion gates (**QOL-07**) so detail checks become enforceable quality gates.

6. Build the new `taskpy check` dashboard (**FEAT-27**) for at-a-glance project health.

## Quick Reference
```bash
# Sprint Intelligence
taskpy sprint                    # Smart dashboard (default)
taskpy sprint init --title "..." # Initialize new sprint
taskpy sprint recommend          # Get task recommendations

# Deploy & Maintenance
bin/deploy.sh                    # Build pip bundle (set TASKPY_PYTHON if needed)
taskpy groom                     # Audit task detail
taskpy manifest rebuild          # Regenerate lost task files from manifest

# Sorting & Filtering
taskpy list --sort created       # Chronological by auto_id
taskpy list --all                # Include done/archived
taskpy kanban --sort priority    # Default priority sort

# Key Files
data/kanban/info/sprint_current.json  # Sprint metadata (tracked in git)
data/kanban/.sequence                 # Auto-increment counter
data/kanban/manifest.tsv              # Task index
```

## Important Notes
- **Kanban data NOT committed**: Task files in `data/kanban/status/` are not in git, only manifest.tsv
- **Sprint metadata IS committed**: `sprint_current.json` tracked for persistence
- **Backup before linking**: Save copies of task files before running `taskpy link` until serialization bug fixed
- **Test sprint active**: Sprint 1 "Sprint Intelligence Implementation" (10 SP capacity, ends 2025-11-30)

## Recent Commits
```
89b1198 feat: implement sprint intelligence system with dashboard and recommendations
cfb324e fix: restore default filtering of done/archived tasks in list view
70758b6 feat: add auto-incrementing sequence ID for task sorting (FEAT-13)
7e94149 fix: make taskpy help and --help show identical output with logo
6417549 feat: update help command to show logo and version by default
```
