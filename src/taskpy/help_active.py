"""
Help text for active status tasks - development workflow.
"""

HELP_ACTIVE = """
==================================================
Active Status: Development Workflow
==================================================

WHAT IS ACTIVE STATUS?
----------------------
Tasks in 'active' status are currently being developed.
This is where you write code, create tests, and prepare
for quality assurance.

GOAL: Implement the feature/fix with proper testing and documentation.

DEVELOPMENT WORKFLOW
--------------------
1. LINK CODE REFERENCES
   As you create/modify files, link them to the task:

     taskpy link TASK-ID --code src/feature.py
     taskpy link TASK-ID --code src/utils/helper.py

2. CREATE TESTS
   Write tests and link them:

     taskpy link TASK-ID --test tests/test_feature.py
     taskpy link TASK-ID --test tests/integration/test_flow.py

3. ADD DOCUMENTATION
   Link documentation files:

     taskpy link TASK-ID --docs docs/feature-guide.md
     taskpy link TASK-ID --docs CHANGELOG.md

4. SET VERIFICATION COMMAND
   Define how to verify the task works:

     taskpy link TASK-ID --verify "pytest tests/test_feature.py -v"

5. RUN VERIFICATION
   Test your changes:

     taskpy verify TASK-ID --update

   Status will update based on test results.

6. PROMOTE TO QA
   When code is ready for review:

     taskpy promote TASK-ID    # active → qa

QUALITY GATE (active → qa)
--------------------------
✓ Code references linked
✓ Test references linked (unless DOCS* task)
✓ Verification command set (unless DOCS* task)
✓ Verification status: PASSED

DOCS* tasks are exempt from test/verification requirements.

COMMON COMMANDS
---------------
View active tasks:
  taskpy list --status active
  taskpy sprint list           # If in current sprint

Link references:
  taskpy link TASK-ID --code PATH
  taskpy link TASK-ID --test PATH
  taskpy link TASK-ID --docs PATH
  taskpy link TASK-ID --verify "COMMAND"

Run verification:
  taskpy verify TASK-ID                    # Run and show results
  taskpy verify TASK-ID --update           # Run and update status

Check requirements:
  taskpy stoplight TASK-ID                 # Check gate requirements
  taskpy info TASK-ID                      # Show status and gates

Track issues:
  taskpy link TASK-ID --issue "Problem description"
  taskpy issues TASK-ID                    # View tracked issues

EXAMPLE WORKFLOW
----------------
  # Start development
  taskpy promote FEAT-10    # ready → active

  # As you work, link files
  taskpy link FEAT-10 --code src/auth/login.py
  taskpy link FEAT-10 --code src/auth/session.py
  taskpy link FEAT-10 --test tests/test_login.py
  taskpy link FEAT-10 --docs docs/auth.md

  # Set up verification
  taskpy link FEAT-10 --verify "pytest tests/test_login.py -xvs"

  # Run tests
  taskpy verify FEAT-10 --update

  # If tests pass, move to QA
  taskpy promote FEAT-10    # active → qa

  # If not ready, stay in active and keep working

TROUBLESHOOTING
---------------
Verification fails:
  • Fix the failing tests
  • Run: taskpy verify TASK-ID --update
  • Check: taskpy issues TASK-ID

Missing gate requirements:
  • Check: taskpy stoplight TASK-ID
  • Link missing references
  • Bypass gates only if urgent: --override (logged)

Need to go back:
  taskpy demote TASK-ID --reason "Needs redesign"
  # active → ready or backlog

TIPS
----
• Link files as you go, don't wait until the end
• Run verification frequently during development
• Use meaningful verification commands that test key functionality
• Track issues/problems with --issue flag for audit trail
• DOCS tasks don't need tests - just link documentation

NEXT STEPS
----------
After moving to QA:
  taskpy help qa              # Learn about QA workflow
  taskpy help regression      # If tests fail in QA

==================================================
"""
