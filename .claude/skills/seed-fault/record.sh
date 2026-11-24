#!/usr/bin/env bash
# Append one seeded-fault record to docs/SEEDED_FAULTS.md with real output:
# the exact change vs HEAD, the test run, and the PostToolUse hook's stderr
# replayed with the payload Claude Code sends for an Edit of each changed
# src/*.py file. Prints RED or GREEN on the last line.
#
#   bash .claude/skills/seed-fault/record.sh "<fault description>"
set -uo pipefail
desc="${1:?usage: record.sh \"<fault description>\"}"
root=$(git rev-parse --show-toplevel) || exit 1
cd "$root" || exit 1
out=docs/SEEDED_FAULTS.md

PY=""
for c in python3 python; do
  if "$c" -c "" >/dev/null 2>&1; then PY=$c; break; fi
done
[ -n "$PY" ] || { echo "record.sh: no working python on PATH" >&2; exit 1; }

change=$(git diff HEAD -- . ':(exclude)docs')
[ -n "$change" ] || { echo "record.sh: nothing differs from HEAD; seed the fault first" >&2; exit 1; }

# Fault number: one more than the fault commits so far, so a second record
# for the same (still uncommitted) fault reuses the number.
n=$(( $(git log --format=%s | grep -cE '^fault( [0-9]+)?:') + 1 ))

tests=$("$PY" -m pytest tests -q --tb=short 2>&1); test_status=$?

{
  printf '\n## Fault %s: %s\n\n' "$n" "$desc"
  printf 'Exact change (`git diff HEAD`):\n\n```diff\n%s\n```\n\n' "$change"
  printf 'Test output (`%s -m pytest tests -q --tb=short`, last 25 lines, exit %s):\n\n```\n%s\n```\n\n' \
    "$PY" "$test_status" "$(printf '%s\n' "$tests" | tail -25)"
  srcs=$(git diff --name-only HEAD -- 'src/*.py')
  if [ -z "$srcs" ]; then
    printf 'Hook: no src/*.py file changed, so the PostToolUse hook (matcher Edit|Write, src/ only) does not fire.\n'
  fi
  for f in $srcs; do
    payload=$("$PY" -c 'import json,sys; print(json.dumps({"hook_event_name": "PostToolUse", "tool_name": "Edit", "tool_input": {"file_path": sys.argv[1]}}))' "$root/$f")
    hook_err=$(printf '%s' "$payload" | CLAUDE_PROJECT_DIR="$root" .claude/hooks/check_leakage.sh 2>&1 >/dev/null)
    hook_status=$?
    printf 'Hook stderr for an Edit of `%s` (exit %s):\n\n```\n%s\n```\n\n' "$f" "$hook_status" "${hook_err:-<empty>}"
  done
} >> "$out"

if [ "$test_status" -eq 0 ]; then
  echo "GREEN: no test caught this fault. Recorded as Fault $n in $out."
else
  echo "RED: tests fail (exit $test_status). Recorded as Fault $n in $out."
fi
