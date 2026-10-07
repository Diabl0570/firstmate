#!/usr/bin/env python3
"""Run existing lifecycle fixtures with CLI/journal evidence, not live harnesses.
Only selects test functions; all assertions execute product interfaces.
Run from the repository worktree with python3 <this-file>.
"""
import os
from pathlib import Path
import re
import subprocess

root = Path.cwd()
evidence = Path(__file__).parent
source = (root / 'tests/fm-control-relaunch.test.sh').read_text()
source = source[:re.search(r'^test_[a-z0-9_]+$', source, re.M).start()]
log = evidence / 'lifecycle-cli-fixture-transcript.log'
log.write_text('Portable fixture evidence only: real Firstmate CLI, fake Herdr transport, renamed Bash agents. No real Claude/Pi or Herdr session.\n')
wrappers = r'''
eval "$(declare -f run_control | sed '1s/run_control/run_control_unlogged/')"
eval "$(declare -f run_spawn | sed '1s/run_spawn/run_spawn_unlogged/')"
record_fixture_call() {
  local interface=$1 dir=$2 out rc
  shift 2
  out=$("${interface}_unlogged" "$dir" "$@"); rc=$?
  {
    printf '\n$ %s %s\nexit=%s\n%s\n' "$interface" "$*" "$rc" "$out"
    printf 'Recorded transport literal writes:\n'
    cat "$dir/fake/literal"
    if [ -f "$dir/fake/agent-pid" ]; then
      printf 'Current fixture-owned process:\n'
      ps -p "$(cat "$dir/fake/agent-pid")" -o pid=,ppid=,args=
    fi
    if [ -f "$dir/home/state/$1.control-relaunch" ]; then
      printf 'Persisted lifecycle journal:\n'
      cat "$dir/home/state/$1.control-relaunch"
    fi
  } >> "$FM_TEST_EVIDENCE_LOG"
  printf '%s\n' "$out"
  return "$rc"
}
run_control() { record_fixture_call run_control "$@"; }
run_spawn() { record_fixture_call run_spawn "$@"; }
test_herdr_missing_registration_never_relaunches_a_surviving_original
test_herdr_relaunch_requires_real_stop_and_replacement_incarnation
test_herdr_relaunch_rechecks_the_shell_at_the_typing_boundary
test_herdr_stop_postcondition_cannot_borrow_a_false_dead_read
'''
driver = root / 'tests/.fm-focused-lifecycle-validation.sh'
driver.write_text(source + wrappers)
env = os.environ.copy()
env.pop('TMPDIR', None)
env['FM_TEST_EVIDENCE_LOG'] = str(log)
try:
    result = subprocess.run(['bash', str(driver)], env=env)
finally:
    driver.unlink(missing_ok=True)
raise SystemExit(result.returncode)
