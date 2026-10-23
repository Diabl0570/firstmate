#!/usr/bin/env bash
# tests/fm-control-herdr-smoke.test.sh - real-herdr smoke test for the agent
# lifecycle control plane (bin/fm-control.sh).
#
# tmux is the control plane's reference backend and is covered hermetically in
# tests/fm-control.test.sh. herdr is the OTHER backend whose recovery-grade
# agent-state classifier the control plane is allowed to trust, so its
# behavior is pinned here against the REAL binary rather than a stub: whether
# an agent is running, and therefore whether a lifecycle verb may act at all,
# comes from registration reconciled with actual process liveness.
#
# No real harness is launched. herdr's `pane report-agent` is the same registry
# the adapter reads, and a symlink named like a harness is the same process
# identity the adapter proves through `pane process-info`, so registering an
# agent over a real agent-named process, over a plain shell, and not at all
# exercises exactly the classification the control plane gates on - including
# the registration Herdr keeps after the agent process is gone (issue #4115).
#
# Always runs on a private, named, throwaway lab session, never the default
# one (tests/herdr-test-safety.sh; the 2026-07-02 incident). Skips cleanly
# when herdr or jq is missing.
set -u

# shellcheck source=tests/lib.sh
. "/Users/kaspersprengers/.no-mistakes/worktrees/6a67f7a4e059/01M5MKV4J3CGFBTWXSKVB7GW3M/tests/lib.sh"

fail() { printf 'not ok - %s\n' "$1" >&2; exit 1; }
pass() { printf 'ok - %s\n' "$1"; }

command -v herdr >/dev/null 2>&1 || { echo "skip: herdr not found"; exit 0; }
command -v jq >/dev/null 2>&1 || { echo "skip: jq not found (required by the herdr adapter)"; exit 0; }

# shellcheck source=tests/herdr-test-safety.sh
. "$ROOT/tests/herdr-test-safety.sh"
herdr_forget_inherited_pane

# The agent-named process below is a symlink to fm_agent_standin's stand-in;
# decide it before any lab session exists so an impossible case skips cleanly.
STANDIN_DIR=$(fm_test_tmproot fm-control-herdr-standin) || {
  printf 'not ok - %s\n' "could not create the stand-in directory" >&2
  exit 1
}
STANDIN_BIN=$(fm_agent_standin "$STANDIN_DIR") || {
  echo "skip: no long-running stand-in binary survives a rename (multicall coreutils, no C compiler)"
  exit 0
}

SESSION="fm-lab-adv-relaunch-$$"
export HERDR_SESSION="$SESSION"
SCRATCH=
LAB_PREPARED=0
cleanup_all() {
  local status=$? cleanup_status=0
  trap - EXIT
  if [ -n "$SCRATCH" ]; then
    if [ -d "$SCRATCH/home/state/hsmoke.git-hooks" ]; then
      chmod u+w "$SCRATCH/home/state/hsmoke.git-hooks" || {
        echo "not ok - could not restore write permission on test git hooks" >&2
        cleanup_status=1
      }
    fi
    fm_test_remove_tree "$SCRATCH" || {
      echo "not ok - could not remove Herdr smoke scratch tree: $SCRATCH" >&2
      cleanup_status=1
    }
  fi
  if [ "$LAB_PREPARED" = 1 ]; then
    herdr_safe_stop_and_delete "$SESSION" || {
      echo "not ok - could not tear down Herdr smoke lab session: $SESSION" >&2
      cleanup_status=1
    }
  fi
  fm_test_cleanup
  [ "$cleanup_status" = 0 ] || status=1
  exit "$status"
}
trap cleanup_all EXIT
fm_herdr_lab_prepare "$SESSION" || fail "could not prepare isolated Herdr lab session"
LAB_PREPARED=1

SCRATCH=$(mktemp -d "${TMPDIR:-/tmp}/fm-control-herdr.XXXXXX")
SCRATCH=$(cd "$SCRATCH" && pwd)
HOME_DIR="$SCRATCH/home"
mkdir -p "$HOME_DIR/state" "$HOME_DIR/data/hsmoke"
cat > "$HOME_DIR/data/hsmoke/brief.md" <<'EOF'
# Task
## Captain's intent
Exercise Herdr lifecycle control safely.

## Firstmate spec
Keep the isolated endpoint and worktree intact.
EOF

# A real git worktree so the control plane's checkpoint has a real local copy.
PROJ="$SCRATCH/proj"
WT="$SCRATCH/wt"
mkdir -p "$PROJ"
git -C "$PROJ" init -q
printf '# proj\n' > "$PROJ/README.md"
git -C "$PROJ" add README.md
git -C "$PROJ" -c user.name='Firstmate Tests' -c user.email='tests@example.invalid' commit -qm initial
git -C "$PROJ" worktree add --quiet -b hsmoke "$WT"
PROJ_REAL=$(cd "$PROJ" && pwd -P)
WT_REAL=$(cd "$WT" && pwd -P)

# shellcheck source=/dev/null
. "$ROOT/bin/fm-backend.sh"
fm_backend_source herdr || fail "fm_backend_source herdr failed"

CONTAINER_RAW=$(fm_backend_herdr_container_ensure "$WT") || fail "container_ensure failed"
CONTAINER=${CONTAINER_RAW%%$'\t'*}
SEEDED_TAB_ID=${CONTAINER_RAW#*$'\t'}
WORKSPACE_ID=${CONTAINER#*:}
TASK_IDS=$(fm_backend_herdr_create_task "$CONTAINER" "fm-hsmoke" "$WT" "$SEEDED_TAB_ID") \
  || fail "create_task failed"
read -r TAB_ID PANE_ID <<EOF
$TASK_IDS
EOF
[ -n "$TAB_ID" ] && [ -n "$PANE_ID" ] || fail "create_task did not return tab/pane ids"

{
  echo "window=$SESSION:$PANE_ID"
  echo "endpoint_task_id=hsmoke"
  echo "worktree=$WT"
  echo "project=$PROJ"
  echo "harness=claude"
  echo "kind=ship"
  echo "mode=no-mistakes"
  echo "yolo=off"
  echo "model=default"
  echo "effort=default"
  echo "backend=herdr"
  echo "herdr_session=$SESSION"
  echo "herdr_workspace_id=$WORKSPACE_ID"
  echo "herdr_tab_id=$TAB_ID"
  echo "herdr_pane_id=$PANE_ID"
} > "$HOME_DIR/state/hsmoke.meta"

run_control() {
  env FM_HOME="$HOME_DIR" HERDR_SESSION="$SESSION" FM_SPAWN_NO_GUARD=1 \
    FM_CONTROL_POLL=0.2 FM_CONTROL_EXIT_WAIT=2 \
    "$ROOT/bin/fm-control.sh" "$@" 2>&1
}

# --- no registered agent: the endpoint exists but hosts no agent ------------

OUT=$(run_control hsmoke exit) || fail "exit against an agent-free herdr pane should be idempotent success: $OUT"
case "$OUT" in
  "already-stopped hsmoke"*) : ;;
  *) fail "an agent-free herdr pane should report already-stopped, got: $OUT" ;;
esac
pass "real herdr: exit on a pane with no registered agent is idempotent success"

# --- the recovery-grade read, against the real binary ------------------------
#
# The classification that decides whether a task can be recovered at all is read
# out of what herdr actually answers, so a stub can only confirm the assumption
# already written into the stub. Its logic is pinned portably in
# tests/fm-backend-herdr.test.sh; this is the check that notices when the real
# client stops answering the way that logic expects, and it names the version so
# a release change is attributed rather than mysterious.
HERDR_VERSION=$(herdr --version 2>&1 | head -1)
HERDR_VERSION=${HERDR_VERSION#herdr }
version_fail() {  # <message>
  fail "$1 [herdr $HERDR_VERSION]"
}

STATE=$(fm_backend_agent_state herdr "$SESSION:$PANE_ID")
[ "$STATE" = dead ] \
  || version_fail "a real, present, agent-free pane reads '$STATE' rather than 'dead'; every relaunch would be refused"

# `status --json` is the second signal, and the only one that answers for a
# session whose operational calls cannot be reached at all. A release that drops
# or renames `.server.running` would silently make every gone endpoint
# unrecoverable again, so it is asserted by name on both a live and an absent
# session.
[ "$(fm_backend_herdr_server_running_state "$SESSION")" = running ] \
  || version_fail "this run's own live lab session does not report .server.running=true through status --json"
[ "$(fm_backend_herdr_server_running_state "fm-lab-never-started-$$")" = stopped ] \
  || version_fail "a session with no server does not report .server.running=false, so authoritative absence can no longer be told from an unreadable read"

# Issue #4091's exact stranding shape: an endpoint recorded in a session whose
# server is not running used to read `unreadable` and block recovery.
[ "$(fm_backend_agent_state herdr "fm-lab-never-started-$$:w1:p2")" = missing ] \
  || version_fail "an endpoint in a session with no running server is not classified as recoverable"

# And the safety direction: an uninterpretable read must never license recovery.
[ "$(fm_backend_agent_state herdr "no-separator-here")" = unreadable ] \
  || version_fail "a malformed endpoint target does not stay unreadable"
pass "real herdr $HERDR_VERSION: a gone session reads recoverable while a live pane and a malformed target do not"

wait_process_state() {  # <expected> <tries>
  local expected=$1 tries=$2 i=0
  while [ "$i" -lt "$tries" ]; do
    [ "$(fm_backend_herdr_pane_process_state "$SESSION" "$PANE_ID")" != "$expected" ] || return 0
    sleep 0.1
    i=$((i + 1))
  done
  return 1
}

stop_replacement() {
  local pid
  pid=$(cat "$SCRATCH/codex-launched")
  kill "$pid" 2>/dev/null || fail "could not stop the inert replacement process"
  wait_process_state shell 50 || fail "the pane did not return to shell-only after stopping the replacement"
}

FAKEBIN="$SCRATCH/fakebin"
AGENT_BIN="$SCRATCH/agentbin"
mkdir -p "$FAKEBIN" "$AGENT_BIN"
ln -s "$STANDIN_BIN" "$AGENT_BIN/codex"
ln -s "$STANDIN_BIN" "$AGENT_BIN/claude"
cat > "$FAKEBIN/codex" <<EOF
#!/usr/bin/env bash
printf '%s\\n' "\$\$" > "$SCRATCH/codex-launched"
exec "$AGENT_BIN/codex" 900
EOF
chmod +x "$FAKEBIN/codex"
printf -v FAKEBIN_Q '%q' "$FAKEBIN"
printf -v PROJ_Q '%q' "$PROJ"
fm_backend_herdr_send_text_line "$SESSION:$PANE_ID" "export PATH=$FAKEBIN_Q:\$PATH" \
  || fail "could not put the inert test harness on the pane PATH"
printf -v AGENT_Q '%q' "$AGENT_BIN/claude"
relaunch() { env FM_HOME="$HOME_DIR" HERDR_SESSION="$SESSION" FM_SPAWN_NO_GUARD=1 "$ROOT/bin/fm-spawn.sh" hsmoke --relaunch --harness codex 2>&1; }
echo "herdr $(herdr --version 2>&1|head -1) session=$SESSION"

# A: an unregistered non-shell, non-agent foreground program occupies the pane.
fm_backend_herdr_send_text_line "$SESSION:$PANE_ID" "sleep 600" || fail "could not start sleep"
wait_process_state other 50 || fail "pane did not read other: $(fm_backend_herdr_pane_process_state "$SESSION" "$PANE_ID")"
echo "A: pane process state=$(fm_backend_herdr_pane_process_state "$SESSION" "$PANE_ID") agent_state=$(fm_backend_agent_state herdr "$SESSION:$PANE_ID")"
rm -f "$SCRATCH/codex-launched"
if OUT=$(relaunch); then fail "A: relaunch over a busy non-shell pane reported success: $OUT"; fi
echo "A: relaunch refused (exit nonzero): $(printf '%s' "$OUT" | grep -v '^warning:' | tail -3)"
sleep 2
[ ! -e "$SCRATCH/codex-launched" ] || fail "A: replacement harness launched despite refusal"
SCREEN=$(fm_backend_herdr_visible_capture "$SESSION:$PANE_ID")
case "$SCREEN" in *codex*) fail "A: launch text was typed into the busy pane";; esac
[ "$(fm_backend_herdr_pane_process_state "$SESSION" "$PANE_ID")" = other ] || fail "A: the foreground program was disturbed"
pass "live herdr adversarial: relaunch refuses a busy non-shell pane, launches nothing, types nothing"
SLEEP_PID=$(herdr pane process-info --pane "$PANE_ID" --session "$SESSION" 2>/dev/null | jq -r '.result.process_info.foreground_processes[0].pid // empty')
kill "$SLEEP_PID"; wait_process_state shell 50 || fail "pane did not return to shell"

# B: a live registered agent that never exits (stand-in ignores /exit).
fm_backend_herdr_send_text_line "$SESSION:$PANE_ID" "$AGENT_Q 900" || fail "start agent"
wait_process_state agent 50 || fail "agent state"
herdr pane report-agent "$PANE_ID" --source adv --agent adv-agent --state idle --session "$SESSION" >/dev/null 2>&1 || fail "register"
echo "B: agent_state=$(fm_backend_agent_state herdr "$SESSION:$PANE_ID")"
rm -f "$SCRATCH/codex-launched"
if OUT=$(relaunch); then fail "B: relaunch reported success while the original agent survives: $OUT"; fi
echo "B: relaunch refused (exit nonzero): $(printf '%s' "$OUT" | grep -v '^warning:' | tail -3)"
sleep 2
[ ! -e "$SCRATCH/codex-launched" ] || fail "B: replacement launched over surviving agent"
[ "$(fm_backend_agent_state herdr "$SESSION:$PANE_ID")" = alive ] || fail "B: original agent not preserved"
grep -q '^harness=claude' "$HOME_DIR/state/hsmoke.meta" || fail "B: meta was rewritten to the replacement harness"
pass "live herdr adversarial: relaunch over a surviving agent fails closed, original agent survives, metadata unchanged"

# C: registration-only (agent process gone, sleep running under registration) must not read as stopped
AGENT_PID=$(herdr pane process-info --pane "$PANE_ID" --session "$SESSION" 2>/dev/null | jq -r '.result.process_info.foreground_processes[0].pid // empty')
kill "$AGENT_PID"; wait_process_state shell 50 || fail "C: shell"
fm_backend_herdr_send_text_line "$SESSION:$PANE_ID" "sleep 600" || fail "C: sleep"
wait_process_state other 50 || fail "C: other"
echo "C: registered=$(herdr agent get "$PANE_ID" --session "$SESSION" 2>/dev/null | jq -r '.result.agent.agent_status // "none"') pane_agent_state=$(fm_backend_herdr_pane_agent_state "$SESSION" "$PANE_ID") agent_state=$(fm_backend_agent_state herdr "$SESSION:$PANE_ID")"
rm -f "$SCRATCH/codex-launched"
if OUT=$(relaunch); then fail "C: relaunch over registration + busy pane reported success: $OUT"; fi
echo "C: relaunch refused (exit nonzero): $(printf '%s' "$OUT" | grep -v '^warning:' | tail -3)"
sleep 2
[ ! -e "$SCRATCH/codex-launched" ] || fail "C: replacement launched"
pass "live herdr adversarial: a registration over a busy non-agent pane never yields relaunch success"
fm_backend_herdr_kill "$SESSION:$PANE_ID" 2>/dev/null || true
