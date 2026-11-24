#!/usr/bin/env bash
# PreToolUse hook (matcher: Bash): refuse shell commands that would write
# into data/raw/. The deny rules in settings.json bind the Write and Edit
# tools only, and check_leakage.sh only watches Edit|Write, so a `cp`, `mv`,
# redirect or `sed -i` from Bash walked straight past both (see
# docs/SEEDED_FAULTS.md, fault 4). This is a string match: a glob or a
# variable can dodge it. The guarantee is the sha256 check in
# src/ingest.py, which every make stage and every test runs.
set -uo pipefail

PY=""
for c in python3 python; do
  if "$c" -c "" >/dev/null 2>&1; then PY=$c; break; fi
done
[ -n "$PY" ] || exit 0

cmd=$(cat | "$PY" -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))')

target='data/raw|bike_daily\.csv'
writes='(^|[^[:alnum:]_.-])(cp|mv|tee|rm|truncate|dd|install|rsync|ln|unlink|shred)([[:space:]]|$)'
writes+='|>{1,2}[[:space:]]*[^[:space:]]*(data/raw|bike_daily\.csv)'
writes+='|(sed|perl)[[:space:]][^|;&]*-i|to_csv|open\([^)]*,[[:space:]]*.[wax]'

if printf '%s' "$cmd" | grep -Eq "$target" && printf '%s' "$cmd" | grep -Eq "$writes"; then
  echo "Blocked by guard_raw.sh: this command would write into data/raw/, which is immutable" \
       "(make data checks its sha256). Read it with pandas, head, wc or sha256sum; write derived" \
       "files to data/processed/. To undo a change: git checkout -- data/raw/" >&2
  exit 2
fi
exit 0
