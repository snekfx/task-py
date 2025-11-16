"""
Help text and documentation for TaskPy CLI.

Separating help content from command logic makes it easier to maintain
and update documentation without touching code.
"""

# Command descriptions for argparse
COMMAND_HELP = {
    "init": "Initialize TaskPy kanban structure in current project",
    "create": "Create a new task under an epic (FEAT, BUGS, DOCS, etc.)",
    "list": "List tasks with optional filters (hides done/archived by default)",
    "show": "Display detailed information for one or more tasks",
    "edit": "Edit a task's markdown file in $EDITOR",
    "promote": "Move task forward in workflow (stub→backlog→ready→active→qa→done→archived)",
    "demote": "Move task backwards in workflow (requires --reason)",
    "move": "Jump task to specific status (requires --reason for non-sequential moves)",
    "info": "Show task status and quality gate requirements",
    "stoplight": "Validate gate requirements (exit codes: 0=ready, 1=missing, 2=blocked)",
    "block": "Block a task with required reason",
    "unblock": "Unblock a task and return to backlog",
    "kanban": "Display kanban board view of all tasks",
    "verify": "Run verification tests for a task and update status",
    "epics": "List available epics from epics.toml",
    "nfrs": "List non-functional requirements from nfrs.toml",
    "milestones": "List project milestones with progress",
    "milestone": "Manage individual milestone (show, start, complete, assign)",
    "link": "Link code/test/doc references or set verification command",
    "issues": "Display tracked issues/problems for a task",
    "history": "Display task state change history and audit trail",
    "resolve": "Resolve a bug task (BUGS*, REG*, DEF*) with special resolution workflow",
    "tour": "Display comprehensive quick reference guide",
    "overrides": "View gate override history log",
    "manifest": "Manage the TSV manifest index (rebuild)",
    "groom": "Audit stub/backlog tasks for sufficient detail depth",
    "session": "Manage work sessions (start, stop, status)",
    "sprint": "Manage sprint task queue (add, remove, list, clear, stats)",
    "stats": "Show project statistics (overall or filtered by epic/milestone)",
}

# Extended epilog for main help
MAIN_EPILOG = """
Common Workflows:
  Create and work on a feature:
    taskpy create FEAT "Add user authentication" --sp 5
    taskpy promote FEAT-01
    taskpy link FEAT-01 --code src/auth.py --test tests/test_auth.py
    taskpy verify FEAT-01 --update
    taskpy promote FEAT-01

  Sprint management:
    taskpy sprint add FEAT-01
    taskpy sprint list
    taskpy sprint stats

  View progress:
    taskpy list --sprint
    taskpy kanban --epic FEAT
    taskpy stats --milestone milestone-1

For comprehensive guide, run: taskpy tour
For more information, see: README.md
"""

TOUR_TEXT = """
==================================================
TaskPy Quick Reference Tour
==================================================

GETTING STARTED
---------------
  taskpy init                           Initialize TaskPy in current project
  taskpy create EPIC "title" --sp N     Create a task with story points
  taskpy create FEAT "feature" --milestone milestone-1  Create with milestone

DAILY WORKFLOW
--------------
  taskpy list                           List all tasks (hides done by default)
  taskpy list --all                     Show all tasks including done/archived
  taskpy list --epic FEAT               Filter by epic
  taskpy list --status backlog          Filter by status
  taskpy list --sprint                  Show sprint tasks only

  taskpy show TASK-ID                   View task details
  taskpy edit TASK-ID                   Edit task in $EDITOR
  taskpy history TASK-ID                View task audit trail
  taskpy history --all                  View all task history

  taskpy promote TASK-ID                Move task forward in workflow
  taskpy demote TASK-ID --reason "why"  Move task backward (requires reason)
  taskpy move TASK-ID status --reason "why"  Jump to specific status (requires reason)
  taskpy block TASK-ID --reason REASON  Block with required reason
  taskpy unblock TASK-ID                Return blocked task to backlog
  taskpy groom                          Audit stub/backlog detail depth
  taskpy stoplight TASK-ID              Gate check (0=ready, 1=missing, 2=blocked)

SPRINT MANAGEMENT
-----------------
  taskpy sprint add TASK-ID             Add task to current sprint
  taskpy sprint remove TASK-ID          Remove from sprint
  taskpy sprint list                    List sprint tasks
  taskpy sprint clear                   Clear entire sprint
  taskpy sprint stats                   Sprint statistics

MILESTONE TRACKING
------------------
  taskpy milestones                     List all milestones (by priority)
  taskpy milestone show milestone-1     Show milestone progress
  taskpy milestone assign TASK-ID milestone-1  Assign task
  taskpy milestone start milestone-2    Mark milestone as active
  taskpy milestone complete milestone-1 Mark milestone done

QUERYING & STATS
----------------
  taskpy list --format ids              List task IDs only
  taskpy list --format tsv              TSV output for scripting
  taskpy stats                          Project statistics
  taskpy stats --epic FEAT              Epic-specific stats
  taskpy stats --milestone milestone-1  Milestone stats
  taskpy kanban                         Kanban board view
  taskpy kanban --epic FEAT             Epic-specific kanban

REFERENCE LINKING & VERIFICATION
---------------------------------
  taskpy link TASK-ID --code src/foo.py         Link source file
  taskpy link TASK-ID --test tests/test_foo.py  Link test file
  taskpy link TASK-ID --docs docs/design.md     Link documentation
  taskpy link TASK-ID --verify "pytest tests/"  Set verification command
  taskpy verify TASK-ID --update                Run and update verification
  taskpy overrides                              View override history

HISTORY & AUDIT
---------------
  taskpy history TASK-ID                View task state change history
  taskpy history --all                  View all task histories
  taskpy overrides                      View gate override log

DATA MAINTENANCE
----------------
  taskpy manifest rebuild               Resync manifest.tsv
  taskpy groom                          Audit stub/backlog detail depth

WORKFLOW STATUSES
-----------------
  stub → backlog → ready → active → qa → done → archived

  stub         Incomplete, needs grooming
  backlog      Groomed, ready for work
  ready        Selected for sprint
  active       Actively being developed
  qa           In testing/review
  regression   Failed QA (branch state)
  done         Completed
  archived     Long-term storage
  blocked      Blocked by dependencies (special state)

QUALITY GATES
-------------
  stub → backlog:  Must have description and acceptance criteria
  active → qa:     Must have code refs, test refs, verification (PASSED)
                   DOCS* tasks exempt from test/verification requirements
  qa → done:       Requires commit hash

USEFUL FLAGS
------------
  --agent                               Agent-friendly output (no boxy formatting)
  --view=data                           Plain output (same as --agent)
  --no-boxy                             Same as --agent
  --all                                 Show all (including done/archived)
  --priority critical|high|medium|low   Set task priority
  --milestone milestone-N               Assign to milestone
  --sp N                                Set story points
  --override                            Bypass validation gates (logged)

NOTE: Global flags work in both positions:
  taskpy --agent list    ✅
  taskpy list --agent    ✅

CONFIGURATION
-------------
  data/kanban/info/epics.toml           Epic definitions
  data/kanban/info/nfrs.toml            Non-functional requirements
  data/kanban/info/milestones.toml      Milestone definitions
  data/kanban/info/config.toml          TaskPy configuration

TIPS
----
  • Tasks stored as markdown in data/kanban/status/
  • Git-friendly: commit config/, ignore task data
  • Use --view=data for scripting/automation
  • Sprint = session-scoped work queue
  • Milestones = multi-phase project organization
  • History tracks all state changes for compliance
  • DOCS tasks don't require test verification

==================================================
"""
