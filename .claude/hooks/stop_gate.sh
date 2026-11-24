#!/usr/bin/env bash
# Stop hook: the agent may not declare itself done while the suite is red.
# Exit 2 sends the failures back and the agent keeps working. If it is
# already continuing because of this hook (stop_hook_active), let it stop,
# so a fault it cannot fix does not loop forever.
set -uo pipefail

PY=""
for c in python3 python; do
  if "$c" -c "" >/dev/null 2>&1; then PY=$c; break; fi
done
[ -n "$PY" ] || exit 0

active=$(cat | "$PY" -c 'import json,sys; print(bool(json.load(sys.stdin).get("stop_hook_active")))')
[ "$active" = "True" ] && exit 0

cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
if ! out=$("$PY" -m pytest tests -q 2>&1); then
  echo "Not done: the test suite is red. Fix it, or say plainly why you cannot." >&2
  echo "$out" | tail -15 >&2
  exit 2
fi
exit 0
