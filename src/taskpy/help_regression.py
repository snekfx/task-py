"""
Help text for regression status - failed QA workflow.
"""

HELP_REGRESSION = """
==================================================
Regression Status: Failed QA Workflow
==================================================

WHAT IS REGRESSION STATUS?
---------------------------
Tasks enter 'regression' status when they fail QA review.
This is a branch state indicating the implementation needs
fixes before it can be marked as done.

GOAL: Fix issues and return to QA, or rework if needed.

HOW TASKS ENTER REGRESSION
---------------------------
A task moves to regression when demoted from QA:

  taskpy demote TASK-ID --reason "Tests failing on edge case"

This automatically moves: qa → regression

REGRESSION WORKFLOW
-------------------
┌─────────┐
│ active  │
└────┬────┘
     │ promote
     ↓
┌─────────┐     demote (fail)
│   qa    │ ───────────────────→ ┌──────────────┐
└────┬────┘                       │  regression  │
     │                            └──────┬───────┘
     │ promote (pass)                    │
     │                            ┌──────┴────────┐
     ↓                            │               │
┌─────────┐              promote │      demote   │
│  done   │              (retry) │   (major fix) │
└─────────┘                      │               │
                                 ↓               ↓
                            ┌─────────┐     ┌─────────┐
                            │   qa    │     │  active │
                            └─────────┘     └─────────┘

TWO PATHS FROM REGRESSION
--------------------------

PATH 1: QUICK FIX (regression → qa)
  For minor fixes that don't require major rework:

    # Fix the issue
    # Re-run verification
    taskpy verify TASK-ID --update

    # If passing, return to QA
    taskpy promote TASK-ID    # regression → qa

PATH 2: MAJOR REWORK (regression → active)
  For significant changes or architectural fixes:

    taskpy demote TASK-ID --reason "Need to refactor approach"
    # regression → active

    # Make major changes, then:
    taskpy promote TASK-ID    # active → qa

TRACKING ISSUES
---------------
When a task enters regression, document what failed:

  taskpy link TASK-ID --issue "Null pointer on empty input"
  taskpy link TASK-ID --issue "Performance regression in large datasets"

View tracked issues:

  taskpy issues TASK-ID

COMMON COMMANDS
---------------
View regression tasks:
  taskpy list --status regression
  taskpy kanban                    # Visual board

Check what failed:
  taskpy issues TASK-ID            # View tracked problems
  taskpy show TASK-ID              # Full task details
  taskpy history TASK-ID           # See why it was demoted

Fix and retry:
  taskpy verify TASK-ID --update   # Re-run verification
  taskpy promote TASK-ID           # regression → qa (if passing)

Major rework:
  taskpy demote TASK-ID --reason "Architectural change needed"
  # regression → active

EXAMPLE WORKFLOW
----------------
# Task fails QA
taskpy demote FEAT-10 --reason "Edge case crashes application"
# qa → regression

# Document the issue
taskpy link FEAT-10 --issue "Crashes when input array is empty"

# Fix the code
# ... make changes ...

# Re-run tests
taskpy verify FEAT-10 --update

# If tests pass, return to QA
taskpy promote FEAT-10    # regression → qa

# If major changes needed
taskpy demote FEAT-10 --reason "Need to redesign validation layer"
# regression → active

QUALITY GATES
-------------
regression → qa:
  Same as active → qa:
  • Code/test references linked
  • Verification command set
  • Verification status: PASSED

regression → active:
  No gate - requires --reason

TIPS
----
• Always document issues with --issue flag for audit trail
• Use regression → qa for quick fixes
• Use regression → active for architectural changes
• Run verification before promoting back to QA
• Check history to understand what failed: taskpy history TASK-ID

AVOIDING REGRESSION
-------------------
• Run verification frequently during development
• Test edge cases before moving to QA
• Use comprehensive test suites
• Review gate requirements: taskpy stoplight TASK-ID

NEXT STEPS
----------
After fixing:
  taskpy help qa              # Understand QA workflow
  taskpy help active          # If returning to development

==================================================
"""
