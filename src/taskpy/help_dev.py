"""
Help text for overall developer workflow.

Shows the complete lifecycle of working with TaskPy from task creation to completion.
"""

HELP_DEV = """
==================================================
TaskPy Developer Workflow Guide
==================================================

OVERVIEW
--------
TaskPy follows a structured workflow with quality gates to ensure
tasks are properly planned, implemented, tested, and documented.

COMPLETE WORKFLOW
-----------------
1. CREATE → 2. GROOM → 3. PLAN → 4. DEVELOP → 5. TEST → 6. COMPLETE

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STEP 1: CREATE TASK
-------------------
Create a new task under the appropriate epic:

  taskpy create FEAT "Add user authentication" --sp 3 --priority high

Task starts in 'stub' status - minimal details, needs grooming.

STEP 2: GROOM TASK (stub → backlog)
------------------------------------
Flesh out the task with full details:

  taskpy edit FEAT-01

Add to the markdown file:
  • Detailed description
  • Acceptance criteria
  • Implementation notes
  • Dependencies

Then promote when ready:

  taskpy promote FEAT-01    # stub → backlog

Quality Gate: Must have description and acceptance criteria.

STEP 3: PLAN SPRINT (backlog → ready)
--------------------------------------
Select tasks for your current sprint:

  taskpy sprint add FEAT-01
  taskpy promote FEAT-01    # backlog → ready

View your sprint:

  taskpy sprint list
  taskpy kanban --sprint

STEP 4: DEVELOP (ready → active → qa)
--------------------------------------
Start working on the task:

  taskpy promote FEAT-01    # ready → active

As you code, link references:

  taskpy link FEAT-01 --code src/auth.py
  taskpy link FEAT-01 --code src/middleware/auth_check.py
  taskpy link FEAT-01 --test tests/test_auth.py
  taskpy link FEAT-01 --docs docs/authentication.md

Set verification command:

  taskpy link FEAT-01 --verify "pytest tests/test_auth.py -v"

When ready for testing:

  taskpy promote FEAT-01    # active → qa

Quality Gate: Must have code refs, test refs, and passing verification.
               (DOCS* tasks exempt from test/verification requirements)

STEP 5: TEST & VERIFY (qa)
---------------------------
Run verification:

  taskpy verify FEAT-01 --update

If tests fail → regression:

  taskpy demote FEAT-01 --reason "Edge case failing"
  # Task moves to 'regression' status

  taskpy link FEAT-01 --issue "Null pointer on empty input"

Fix and retry:

  taskpy promote FEAT-01    # regression → qa

Or major rework needed:

  taskpy demote FEAT-01 --reason "Need architectural changes"
  # regression → active

STEP 6: COMPLETE (qa → done)
-----------------------------
Once verification passes, mark as done with commit hash:

  taskpy promote FEAT-01 --commit abc123f

Task moves to 'done' status.

Quality Gate: Requires git commit hash.

SPECIAL WORKFLOWS
-----------------

BUG RESOLUTION
--------------
For bugs that don't need code changes:

  taskpy resolve BUGS-05 --resolution duplicate \\
    --duplicate-of BUGS-01 --reason "Same root cause"

  taskpy resolve BUGS-03 --resolution cannot_reproduce \\
    --reason "Unable to reproduce on latest version"

Resolution types:
  • duplicate - Duplicate of another issue
  • cannot_reproduce - Unable to reproduce
  • wont_fix - Working as intended
  • config_change - Fixed via config
  • docs_only - Fixed with documentation

BLOCKING TASKS
--------------
If a task is blocked by dependencies:

  taskpy block FEAT-10 --reason "Waiting for API endpoint FEAT-08"

Unblock when ready:

  taskpy unblock FEAT-10    # Returns to backlog

VIEWING PROGRESS
----------------
  taskpy list --sprint           # Current sprint tasks
  taskpy kanban                  # Visual board
  taskpy stats                   # Project statistics
  taskpy history FEAT-01         # Task audit trail
  taskpy history --all           # All task history

USEFUL FLAGS
------------
  --all           Show done/archived tasks
  --agent         Plain output for automation
  --override      Bypass gates (logged, use sparingly)

For stage-specific help:
  taskpy help stub        # Grooming incomplete tasks
  taskpy help active      # Development workflow details
  taskpy help qa          # Testing and verification
  taskpy help regression  # Failed QA workflow

==================================================
"""
