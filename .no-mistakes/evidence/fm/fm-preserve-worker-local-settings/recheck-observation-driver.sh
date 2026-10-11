#!/usr/bin/env bash
set -u

phase_capture() {
  python3 "$PHASE_CAPTURE" "$TMP_ROOT" "$ROOT" "$@"
}

test_observed_adapter() {
  local definition
  definition=$(declare -f run_spawn)
  eval "${definition/run_spawn/phase_original_run_spawn}"
  run_spawn() {
    local output status settings="$2/.claude/settings.local.json" state="$1/state" id="$4"
    phase_capture fm-spawn before 0 "$settings" "$state" "$id" </dev/null
    output=$(phase_original_run_spawn "$@"); status=$?
    printf '%s' "$output" | phase_capture fm-spawn after "$status" "$settings" "$state" "$id"
    printf '%s\n' "$output"
    return "$status"
  }
  "$PHASE_CASE"
}

test_observed_relaunch() {
  local definition
  definition=$(declare -f run_control)
  eval "${definition/run_control/phase_original_run_control}"
  run_control() {
    local output status settings="$1/wt/.claude/settings.local.json" state="$1/home/state" id="$2"
    [ ! -d "$1/smhome" ] || settings="$1/smhome/.claude/settings.local.json"
    phase_capture fm-control before 0 "$settings" "$state" "$id" </dev/null
    output=$(phase_original_run_control "$@"); status=$?
    printf '%s' "$output" | phase_capture fm-control after "$status" "$settings" "$state" "$id"
    printf '%s\n' "$output"
    return "$status"
  }
  "$PHASE_CASE"
}

test_observed_partial_write() {
  local rec id=worker-partial-proof output settings prior rc
  rec=$(make_spawn_case worker-partial-proof claude "$id")
  read_case_record "$rec"
  settings="$WT_DIR/.claude/settings.local.json"
  prior="$CASE_DIR/prior.json"
  mkdir -p "${settings%/*}"
  printf '.claude/settings.local.json\n' >> "$PROJ_DIR/.git/info/exclude"
  jq -n '{permissions: {allow: ["Read(./docs/**)"]}, env: {FIXTURE_FLAG: "preserve"}, savedFixture: ("x" * 3800)}' > "$prior"
  cp "$prior" "$settings"
  chmod 640 "$settings"
  phase_capture fm-spawn before 0 "$settings" "$HOME_DIR/state" "$id" </dev/null
  output=$(ulimit -c 0; ulimit -f 4; run_spawn "$HOME_DIR" "$WT_DIR" "$FAKEBIN_DIR" "$id" "$PROJ_DIR"); rc=$?
  printf '%s' "$output" | phase_capture fm-spawn partial-write-refusal "$rc" "$settings" "$HOME_DIR/state" "$id"
  expect_code 1 "$rc" "partial write must be a normal refusal: $output"
  assert_contains "$output" 'could not publish refreshed Claude worker hooks' 'missing publication refusal'
  cmp -s "$prior" "$settings" || fail 'partial write changed original bytes'
  [ -n "$(find "$settings" -prune -perm 640)" ] || fail 'partial write changed original mode'
  [ "$(ls -A "${settings%/*}")" = settings.local.json ] || fail 'partial write left staged output'
  output=$(run_spawn "$HOME_DIR" "$WT_DIR" "$FAKEBIN_DIR" "$id" "$PROJ_DIR"); rc=$?
  printf '%s' "$output" | phase_capture fm-spawn unrestricted-retry "$rc" "$settings" "$HOME_DIR/state" "$id"
  expect_code 0 "$rc" "unrestricted retry must succeed: $output"
  jq -e --slurpfile prior "$prior" 'del(.hooks) == $prior[0]' "$settings" >/dev/null || fail 'retry lost saved settings'
  [ -n "$(find "$settings" -prune -perm 640)" ] || fail 'retry changed original mode'
  [ "$(ls -A "${settings%/*}")" = settings.local.json ] || fail 'retry left staged output'
  pass 'real partial write refused, original bytes/mode retained, staging removed, unrestricted retry succeeded'
}
export -f phase_capture test_observed_adapter test_observed_relaunch test_observed_partial_write
export PHASE_CAPTURE="$PWD/.phase-test/capture-state.py"
export FM_TEST_SKIP_ORPHAN_REAP=1
export PHASE_EVIDENCE="${EVIDENCE_DIR:?set the dedicated evidence directory}/recheck-product-state.jsonl"

FM_TEST_ONLY=test_observed_partial_write TMPDIR="$PWD/.phase-test/tmp" bash bin/fm-test-run.sh tests/fm-busy-adapter-wiring.test.sh || exit
for PHASE_CASE in test_claude_worker_settings_preserved test_claude_worker_settings_publish_failures_keep_original; do
  export PHASE_CASE
  FM_TEST_ONLY=test_observed_adapter TMPDIR="$PWD/.phase-test/tmp" bash bin/fm-test-run.sh tests/fm-busy-adapter-wiring.test.sh || exit
done
for PHASE_CASE in test_relaunch_keeps_worker_local_settings_and_refreshes_only_firstmate_hooks test_malformed_worker_settings_refuse_relaunch_untouched test_failed_worker_settings_publication_refuses_relaunch_untouched test_prepublication_abort_keeps_worker_local_settings test_secondmate_claude_relaunch_keeps_local_settings; do
  export PHASE_CASE
  env -u TMPDIR FM_TEST_ONLY=test_observed_relaunch bash bin/fm-test-run.sh tests/.phase-settings-relaunch.test.sh || exit
done
