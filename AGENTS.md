# Builder Rules (Shared by all Agents)

## Hard Constraints
- Only modify files explicitly listed in the task's Allowed files
- If you need to modify an unlisted file, stop and explain — never decide on your own
- Do not add any feature, config, abstraction, or refactor not requested in the task
- Every line of code changed must trace back to a specific requirement in the task
- When fixing issues, only change what is broken — never rewrite the whole file

## Workflow
- Work on one task at a time
- After completing a task, wait for Reviewer approval before starting the next one

## Git Rules
- Never run git commit / push / merge on your own
- All git operations require explicit user confirmation
- Commit format: type: description
- Allowed types: feat / fix / docs / refactor / test

## Stop Conditions — Must write to QA file, never self-decide

You MUST stop and write a QA entry in the following situations:
- You need to modify a file not in Allowed files or listed in Forbidden files
- An interface behavior is not defined in ARCHITECTURE.md
- There are two or more equally valid implementation approaches
- You need to introduce a third-party library
- The task description is ambiguous

For clear technical details with an obvious answer, you may decide on your own without writing a QA.

QA entry format:
  ## Q[number]
  Status: ⏳ Pending
  From: Builder-[module]
  Task: [current task]
  [Question]
  [your question here]

After writing, stop and notify the user: "Question submitted, waiting for Planner response."
After being notified, read .agent/qa/current_qa.md for the answer and continue.

## Done
After completing a task, report: "Done. Verification: [specific result]"