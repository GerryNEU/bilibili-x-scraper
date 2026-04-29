---
name: Task approval workflow — 5 steps
description: What to output each time a Reviewer approves a task
type: feedback
---

When a Reviewer approves a task, always output all 5 steps in order:

1. Confirm task complete
2. Output commit instructions for Builder (branch, files to stage, commit message format)
3. Remind user to open a new Builder thread for the next task
4. Archive any resolved QA entries
5. Output the next task — both the Builder task instruction file and the Reviewer Prompt

**Why:** User established this as the standard handoff protocol after Task 02 approval.  
**How to apply:** Every time the user says "Reviewer approved Task N", immediately run all 5 steps without waiting to be asked.
