"""
Help text for stub status tasks - grooming and planning.
"""

HELP_STUB = """
==================================================
Stub Status: Grooming Incomplete Tasks
==================================================

WHAT IS STUB STATUS?
--------------------
Tasks in 'stub' status are incomplete and need grooming before
they can be worked on. They may have just a title or minimal
details.

GOAL: Add enough detail so the task is ready for sprint planning.

REQUIRED TO PROMOTE (stub → backlog)
------------------------------------
✓ Description - What needs to be done and why
✓ Acceptance Criteria - How to know when it's complete

GROOMING CHECKLIST
------------------
1. Open the task for editing:

     taskpy edit TASK-ID

2. Add a detailed description:
   • What problem does this solve?
   • Why is this important?
   • Any context or background needed

3. Define acceptance criteria:
   • [ ] Clear, testable outcomes
   • [ ] Edge cases considered
   • [ ] Success conditions defined

4. Optional but helpful:
   • Implementation notes/approach
   • Dependencies on other tasks
   • Links to related issues/discussions
   • Estimated story points (--sp flag)

5. Promote when ready:

     taskpy promote TASK-ID    # stub → backlog

COMMON COMMANDS
---------------
View stub tasks:
  taskpy list --status stub
  taskpy kanban

Audit stub details:
  taskpy groom                 # Shows stub tasks needing grooming

Edit task:
  taskpy edit TASK-ID

Set story points:
  taskpy edit TASK-ID          # Add story_points in frontmatter

EXAMPLES
--------
Good stub → backlog transition:

  Before (stub):
    Title: Add caching
    Description: (empty)

  After (backlog):
    Title: Add caching
    Description: Implement Redis caching for API responses
                 to reduce database load and improve response times.

    Acceptance Criteria:
    - [ ] Cache GET requests for 5 minutes
    - [ ] Invalidate cache on data updates
    - [ ] Add cache hit/miss metrics
    - [ ] Handle Redis connection failures gracefully

TIPS
----
• Don't over-plan - enough detail to start is sufficient
• Use taskpy groom to find tasks needing attention
• Link related tasks with dependencies field
• Use --override only if you need to bypass gates temporarily

NEXT STEPS
----------
After grooming to backlog:
  taskpy help backlog          # Learn about sprint planning
  taskpy help dev              # See complete workflow

==================================================
"""
