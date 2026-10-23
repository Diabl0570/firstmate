#!/usr/bin/env bash
# Manual CLI drive of fm-contributions.sh poll against a fake failing gh.
set -u
WT=$1
cd "$WT"
. tests/lib.sh
TMP_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/fm-contrib-drive.XXXXXX")
NOW=2026-09-16T08:00:00Z
HEAD_A=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
REAL_DATE=$(command -v date)
eval "$(sed -n '/^new_home() {/,/^}/p;/^record() {/,/^}/p;/^mutate_record() {/,/^}/p;/^forge_home() {/,/^}/p;/^with_home() {/,/^}/p' tests/fm-contributions.test.sh)"
eval "$(awk '/^wrap_forge\(\) \{/{on=1} on{print} on&&/chmod \+x "\$home\/fakebin\/gh" "\$home\/fakebin\/date"/{done=1} done&&/^}/{exit}' tests/fm-contributions.test.sh)"
run() { # name fault [env...]
  local name=$1 fault=$2; shift 2
  local home; home=$(new_home "$name"); forge_home "$home"; wrap_forge "$home"
  mutate_record "$home" delivery '.records[0].checked_at="2026-09-15T08:00:00Z"'
  printf '%s\n' "$fault" > "$home/forge/fault"
  echo "===== scenario: $name (gh fault: $fault) ====="
  echo "\$ fm-contributions.sh poll"
  with_home "$home" env "$@" "$ROOT/bin/fm-contributions.sh" poll; echo "[exit $?]"
  echo "--- persisted record error:"; jq -r '.records[0].error' "$home/data/delivery/contributions.json"
  echo "--- persisted record pending count:"; jq -r '.records[0].pending|length' "$home/data/delivery/contributions.json"
  echo "--- sentinel/raw-stderr leak check across home (data+state):"
  if grep -rq 'PRIVATE_DIAGNOSTIC_SENTINEL\|xxxxxxxxxx' "$home/data" "$home/state" 2>/dev/null; then echo LEAK; else echo 'no PRIVATE_DIAGNOSTIC_SENTINEL / raw stderr in persisted state'; fi
  echo "--- gh calls for failing stage(s):"; sort "$home/forge/calls" | uniq -c | sed 's/^ */  /'
  echo
}
run private-both private-500-both
run private-checks private-500-checks
run oversized oversized-error
run boundary boundary-http
run invalid-status invalid-http
run silent silent-failure
run head-drift head
run transient-once fail-once
FORGE_ERROR_TEXT='error connecting to no-such-host-f67.invalid' run dns real-reviews FORGE_ERROR_TEXT='error connecting to no-such-host-f67.invalid'
rm -rf "$TMP_ROOT"
