#!/usr/bin/env bash
set -u

test_fixture_settings_unreadable() {
  local rec id=worker-unreadable out settings prior rc
  rec=$(make_spawn_case worker-unreadable claude "$id")
  read_case_record "$rec"
  settings="$WT_DIR/.claude/settings.local.json"
  prior="$CASE_DIR/prior.json"
  mkdir -p "${settings%/*}"
  printf '.claude/settings.local.json\n' >> "$PROJ_DIR/.git/info/exclude"
  printf '%s\n' '{"permissions":{"allow":["Read(./docs/**)"]},"env":{"FIXTURE_FLAG":"preserve"}}' > "$prior"
  cp "$prior" "$settings"
  chmod 000 "$settings"
  out=$(run_spawn "$HOME_DIR" "$WT_DIR" "$FAKEBIN_DIR" "$id" "$PROJ_DIR"); rc=$?
  expect_code 1 "$rc" "unreadable settings must refuse spawn: $out"
  assert_contains "$out" 'could not refresh Claude worker hooks without losing existing settings' 'unreadable settings did not surface their safety refusal'
  [ -n "$(find "$settings" -prune -perm 000)" ] || fail 'unreadable settings mode changed'
  chmod 600 "$settings"
  cmp -s "$prior" "$settings" || fail 'unreadable settings bytes changed'
  [ "$(ls -A "${settings%/*}")" = settings.local.json ] || fail 'unreadable refusal left staged output'
  pass 'unreadable settings refuse publication without changing bytes or mode'
}
export -f test_fixture_settings_unreadable
FM_TEST_ONLY=test_fixture_settings_unreadable bash bin/fm-test-run.sh tests/fm-busy-adapter-wiring.test.sh > .phase-test/unreadable.txt 2>&1
rc=$?
printf 'Unreadable fixture runner exit=%s\n' "$rc"
[ "$rc" -eq 0 ] || exit 1

FM_TEST_ONLY=test_unknown_focused_function bash bin/fm-test-run.sh tests/fm-busy-adapter-wiring.test.sh > .phase-test/selector-unknown.txt 2>&1
rc=$?
printf 'Unknown selection runner exit=%s (expected 1)\n' "$rc"
[ "$rc" -eq 1 ] || exit 1

test_selected_exit_37() { return 37; }
export -f test_selected_exit_37
FM_TEST_ONLY=test_selected_exit_37 bash bin/fm-test-run.sh tests/fm-busy-adapter-wiring.test.sh > .phase-test/selector-failing.txt 2>&1
rc=$?
printf 'Selected failure runner exit=%s (expected 1)\n' "$rc"
[ "$rc" -eq 1 ] || exit 1
grep -q 'exit=37 ' .phase-test/selector-failing.txt || exit 1

FM_TEST_ONLY=test_claude_hooks_stale_incarnation_harmless bash bin/fm-test-run.sh tests/fm-busy-adapter-wiring.test.sh > .phase-test/selector-passing.txt 2>&1
rc=$?
printf 'Valid selection runner exit=%s (expected 0)\n' "$rc"
[ "$rc" -eq 0 ] || exit 1
