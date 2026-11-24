---
name: seed-fault
description: Seed one deliberate fault described in the arguments, prove that a test goes red and the PostToolUse hook fires, record the real output in docs/SEEDED_FAULTS.md, then fix it. Use when asked to break the pipeline on purpose or to check that a guard works.
argument-hint: <fault, e.g. "delete the .shift(1) from cnt_lag_7">
allowed-tools:
  - Read
  - Edit
  - Bash(git status *)
  - Bash(git log *)
  - Bash(git diff *)
  - Bash(git add *)
  - Bash(git commit *)
  - Bash(make *)
  - Bash(python -m pytest *)
  - Bash(bash .claude/skills/seed-fault/record.sh *)
  - Bash(bash ${CLAUDE_SKILL_DIR}/record.sh *)
---

# Working tree before seeding (must be empty)

!`git status --short`

# Last commit

!`git log --oneline -1`

# Fault to seed: $ARGUMENTS

Work in this order. Paste output; never describe it.

1. **Start clean.** If the status above lists any file, stop and say so: a
   fault seeded on a dirty tree cannot be cleanly undone.
2. **Seed it.** Make the single smallest Edit that implements the fault.
   Change nothing else. If the Edit touches `src/`, the PostToolUse hook
   runs and its message appears to you; quote it.
3. **Record it:** `bash .claude/skills/seed-fault/record.sh "$ARGUMENTS"`.
   It appends the exact diff, the test output and the hook's stderr to
   `docs/SEEDED_FAULTS.md`, and its last line says RED or GREEN.
4. **If GREEN, the suite missed the fault. That is the finding.** Write the
   missing test in `tests/` (it must fail now, for this fault), then record
   again: `bash .claude/skills/seed-fault/record.sh "$ARGUMENTS, with the new test"`.
   It must now say RED.
5. **Commit the fault:** `git add src tests` then
   `git commit -m "fault: $ARGUMENTS"`. Leave `docs/` unstaged.
6. **Fix it** with the fewest edits: undo the seeded change, keep any new
   test. Run `make test` until it passes. Count your turns, one tool call
   per turn, from the RED line to the first green `make test`.
7. **Close the record.** Append one line to the end of
   `docs/SEEDED_FAULTS.md`: `Turns to fix: N (what you did).` Then
   `git add -A` and `git commit -m "fix: $ARGUMENTS"`.

Never seed a fault in `data/raw/`: the raw CSV is immutable.
