#!/usr/bin/env bash
# PostToolUse hook: re-run the leakage tests whenever src/ changes.
#
# This runs AFTER the edit has landed, so it cannot prevent the write. What
# exit 2 does is send stderr back to Claude as a system message, so the
# failure is in front of the agent immediately and it cannot carry on as if
# the edit were fine. The Stop hook (stop_gate.sh) makes "done" itself
# conditional on the whole suite.
set -uo pipefail

# First interpreter that actually runs. On Windows `python3` is often a
# Store alias that exits non-zero, which used to leave $path empty and make
# this hook pass silently.
PY=""
for c in python3 python; do
  if "$c" -c "" >/dev/null 2>&1; then PY=$c; break; fi
done
[ -n "$PY" ] || { echo "check_leakage.sh: no working python; leakage tests NOT run" >&2; exit 1; }

payload=$(cat)
path=$(printf '%s' "$payload" | "$PY" -c \
  'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))')
path=${path//\\//}   # Windows paths arrive as C:\...\src\x.py

case "$path" in
  *src/*.py) ;;
  *) exit 0 ;;
esac

cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
if ! out=$("$PY" -m pytest tests/test_leakage.py -q 2>&1); then
  echo "Leakage tests failed after editing $path:" >&2
  echo "$out" | tail -20 >&2
  exit 2
fi
exit 0
