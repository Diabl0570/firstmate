#!/usr/bin/env bash
# Focused live driver: runs the real remote-job library, detached supervisor,
# serving child, heartbeat and command lane in a disposable checkout/account.
set -u
umask 077
ROOT=$PWD
SOURCE=${1:-head}
CASE=${2:-all}
BASE=9ea0c41a480cf965b80bba60a80701639f70f723
TMP_ROOT=$(mktemp -d "$PWD/.remote-live.XXXXXX") || exit 1
REMOTE_ROOT=$TMP_ROOT/root
ACCOUNT=$TMP_ROOT/account
JOB_HOME=$TMP_ROOT/home
STATE=$TMP_ROOT/queue
SHIM=$TMP_ROOT/shim
GATE=$TMP_ROOT/gate
BASE_PATH=$PATH
OWNER=
GROUP=
mkdir -p "$REMOTE_ROOT/bin" "$ACCOUNT" "$JOB_HOME" "$SHIM" "$GATE"
cp "$ROOT/AGENTS.md" "$REMOTE_ROOT/AGENTS.md"
for file in fm-remote-job-lib.sh fm-remote-job-worker.sh fm-remote-delta-read.sh; do
  if [ "$SOURCE" = base ]; then
    git show "$BASE:bin/$file" > "$REMOTE_ROOT/bin/$file" || exit 1
  else
    cp "$ROOT/bin/$file" "$REMOTE_ROOT/bin/$file"
  fi
done
chmod +x "$REMOTE_ROOT/bin/"*.sh
GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null git -C "$REMOTE_ROOT" init -q -b main
GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null git -C "$REMOTE_ROOT" add AGENTS.md bin
export FM_REMOTE_JOB_STATE_ROOT=$STATE FM_REMOTE_JOB_PLATFORM_OVERRIDE=Linux
export FM_REMOTE_JOB_QUEUE_TIMEOUT=20 FM_REMOTE_JOB_TIMEOUT=10
unset FM_REMOTE_JOB_ACTIVE FM_ROOT_OVERRIDE FM_HOME FM_GATE_REFUSE_BYPASS
. "$REMOTE_ROOT/bin/fm-remote-job-lib.sh"
fail() { printf 'FAIL: %s\n' "$*" >&2; if [ -f "$STATE/logs/dev.firstmate.remote-job.log" ]; then tail -n 35 "$STATE/logs/dev.firstmate.remote-job.log" >&2; fi; exit 1; }
cleanup() {
  : > "$GATE/release"
  : > "$GATE/link-release"
  local group
  for group in $(ps -eo pgid=,args= | awk -v w="$REMOTE_ROOT/bin/fm-remote-job-worker.sh" '$3 == w {print $1}' | sort -u); do
    kill -CONT -- "-$group" 2>/dev/null || true
    kill -TERM -- "-$group" 2>/dev/null || true
  done
  /bin/sleep 1
  for group in $(ps -eo pgid=,args= | awk -v w="$REMOTE_ROOT/bin/fm-remote-job-worker.sh" '$3 == w {print $1}' | sort -u); do
    kill -KILL -- "-$group" 2>/dev/null || true
  done
  printf 'Cleanup: disposable worker processes signalled; checkout, account and queue removed.\n'
  rm -rf -- "$TMP_ROOT"
}
trap cleanup EXIT
REAL_MV=$(command -v mv)
REAL_LN=$(command -v ln)
REAL_TOUCH=$(command -v touch)
export LIVE_STATE=$STATE LIVE_GATE=$GATE LIVE_REAL_MV=$REAL_MV LIVE_REAL_LN=$REAL_LN LIVE_REAL_TOUCH=$REAL_TOUCH
printf '#!/bin/bash\nfor target; do :; done\nif [ "$target" = "$LIVE_STATE/${LIVE_BARRIER:-never}" ]; then\n  : > "$LIVE_GATE/blocked"\n  for ((i=0;i<1200;i++)); do\n    [ -f "$LIVE_GATE/release" ] && break\n    /bin/sleep 0.05\n  done\nfi\nexec "$LIVE_REAL_MV" "$@"\n' > "$SHIM/mv"
printf '#!/bin/bash\nfor target; do :; done\nif [ "$target" = "$LIVE_STATE/worker.ready" ] && [ -f "$LIVE_GATE/link-arm" ]; then\n  : > "$LIVE_GATE/link-blocked"\n  for ((i=0;i<1200;i++)); do\n    [ -f "$LIVE_GATE/link-release" ] && break\n    /bin/sleep 0.05\n  done\nfi\nexec "$LIVE_REAL_LN" "$@"\n' > "$SHIM/ln"
printf '#!/bin/bash\nlast=${!#}\nif [ "$last" -ef "$LIVE_STATE/worker.ready" ] && [ -f "$LIVE_GATE/stale-arm" ]; then\n  printf "%%s\\n" "$last" > "$LIVE_GATE/touch-observed"\n  exit 0\nfi\nexec "$LIVE_REAL_TOUCH" "$@"\n' > "$SHIM/touch"
chmod +x "$SHIM/mv" "$SHIM/ln" "$SHIM/touch"
wait_file() { for ((i=0;i<200;i++)); do [ -f "$1" ] && return 0; /bin/sleep 0.05; done; fail "file not published: $1"; }
wait_ready() { fm_remote_job_wait_for_probe "$REMOTE_ROOT" "$ACCOUNT" || fail "$FM_REMOTE_JOB_ERROR"; }
get_owner() {
  OWNER=$(<"$STATE/worker.lock/pid")
  GROUP=$(fm_remote_job_process_pgid "$OWNER") || fail 'cannot resolve worker group'
  fm_remote_job_lock_owner_matches_process "$ACCOUNT" || fail 'owner verification failed'
}
groups() { ps -eo pgid=,args= | awk -v w="$REMOTE_ROOT/bin/fm-remote-job-worker.sh" '$3 == w {print $1}' | sort -u; }
show_tree() {
  printf 'Published owner=%s group=%s; worker process inventory:\n' "$OWNER" "$GROUP"
  ps -eo pid=,ppid=,pgid=,state=,args= | awk -v w="$REMOTE_ROOT/bin/fm-remote-job-worker.sh" '$5 == "/bin/bash" && $6 == w'
}
stop() {
  fm_remote_job_stop_worker_tree "$OWNER" || fail 'worker tree did not stop safely'
  OWNER= GROUP=
  rm -rf -- "$STATE"
}
start() {
  FM_REMOTE_JOB_REPAIRED=0
  PATH="$SHIM:$BASE_PATH" fm_remote_job_start_linux_worker "$REMOTE_ROOT" "$ACCOUNT" || fail "$FM_REMOTE_JOB_ERROR"
  wait_ready
  get_owner
}
job() {
  local id status
  printf 'live remote worker survived %s\n' "$1" > "$JOB_HOME/result.log"
  fm_remote_job_stage "$ACCOUNT" "$REMOTE_ROOT" "$JOB_HOME" fm-remote-delta-read.sh result.log 0 e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 0 </dev/null >/dev/null || fail "$FM_REMOTE_JOB_ERROR"
  id=$FM_REMOTE_JOB_ID
  fm_remote_job_wait "$ACCOUNT" "$id" || fail "$FM_REMOTE_JOB_ERROR"
  status=$(fm_remote_job_read_state "$STATE/jobs/$id")
  printf 'Command result: id=%s state=%s exit=%s\n' "$id" "$status" "$FM_REMOTE_JOB_EXIT"
  printf '%s\n' "$(<"$FM_REMOTE_JOB_STDOUT")"
  [ "$status" = done ] && [ "$FM_REMOTE_JOB_EXIT" = 0 ] || fail 'remote job did not complete'
  grep -Fx "live remote worker survived $1" "$FM_REMOTE_JOB_STDOUT" >/dev/null || fail 'real delta-read command did not relay fixture content'
  fm_remote_job_reap "$ACCOUNT" "$id" || fail 'result could not be reaped'
}
initialization() {
  local pid_state=$1 barrier=$2 original repaired
  printf '\nSCENARIO initialization: public-pid=%s publication-barrier=%s\n' "$pid_state" "$barrier"
  rm -f "$GATE/blocked" "$GATE/release"
  fm_remote_job_prepare_state "$ACCOUNT" || fail "$FM_REMOTE_JOB_ERROR"
  if [ "$pid_state" = stale ]; then printf '%s\n' "$$" > "$STATE/worker.pid"; fi
  PATH="$SHIM:$BASE_PATH" LIVE_BARRIER="$barrier" fm_remote_job_start_linux_worker "$REMOTE_ROOT" "$ACCOUNT" || fail "$FM_REMOTE_JOB_ERROR"
  wait_file "$GATE/blocked"
  get_owner
  original=$OWNER
  [ ! -e "$STATE/worker.ready" ] || fail 'readiness already published'
  if [ "$barrier" = worker.identity ]; then
    [ ! -e "$STATE/worker.identity" ] || fail 'identity already published'
  else
    fm_remote_job_worker_identity_matches "$REMOTE_ROOT" "$ACCOUNT" || fail 'identity missing before PID publication'
  fi
  printf 'Verified lock pid/start/command; ready absent; worker.identity=%s; worker.pid=%s\n' "$(if [ -f "$STATE/worker.identity" ]; then printf published; else printf absent; fi)" "$(if [ -f "$STATE/worker.pid" ]; then printf '%s' "$(<"$STATE/worker.pid")"; else printf absent; fi)"
  repaired=$(
    FM_REMOTE_JOB_REPAIRED=0
    fm_remote_job_start_linux_worker "$REMOTE_ROOT" "$ACCOUNT" || exit 1
    printf '%s' "$FM_REMOTE_JOB_REPAIRED"
  ) || fail 'concurrent start failed'
  show_tree
  printf 'Concurrent start repaired=%s; distinct worker groups=%s\n' "$repaired" "$(groups | tr '\n' ' ')"
  [ "$repaired" = 0 ] && [ "$(groups)" = "$GROUP" ] || fail 'concurrent start launched another supervisor or killed initializing owner'
  : > "$GATE/release"
  wait_ready
  [ "$(<"$STATE/worker.pid")" = "$original" ] || fail 'owner changed while initialization completed'
  job "initialization-$pid_state-$barrier"
  stop
}
aged() {
  local repaired original
  printf '\nSCENARIO aged heartbeat: repeat start beside a verified live frozen owner\n'
  start
  original=$OWNER
  kill -STOP -- "-$GROUP"
  /bin/sleep 0.2
  touch -t 200001010000 "$STATE/worker.ready"
  if fm_remote_job_probe "$ACCOUNT"; then fail 'old readiness incorrectly accepted'; fi
  repaired=$(
    FM_REMOTE_JOB_REPAIRED=0
    fm_remote_job_start_linux_worker "$REMOTE_ROOT" "$ACCOUNT" || exit 1
    printf '%s' "$FM_REMOTE_JOB_REPAIRED"
  ) || fail 'aged-heartbeat start failed'
  show_tree
  printf 'Heartbeat mtime=%s; readiness probe rejected; concurrent start repaired=%s; distinct groups=%s\n' "$(fm_remote_job_path_mtime "$STATE/worker.ready")" "$repaired" "$(groups | tr '\n' ' ')"
  [ "$repaired" = 0 ] && [ "$(groups)" = "$GROUP" ] || fail 'aged readiness duplicated the verified live lock owner'
  # Drive the full caller ensure boundary too: it must wait for readiness,
  # without adding a supervisor while the verified owner is frozen.
  (
    fm_remote_job_ensure_worker "$REMOTE_ROOT" "$ACCOUNT" || exit 1
    printf 'Full ensure completed; repaired=%s owner=%s\n' "$FM_REMOTE_JOB_REPAIRED" "$(<"$STATE/worker.lock/pid")"
  ) > "$TMP_ROOT/ensure-result" 2>&1 &
  local caller=$!
  /bin/sleep 1
  kill -0 "$caller" 2>/dev/null || fail 'full ensure accepted aged readiness without waiting'
  [ "$(groups)" = "$GROUP" ] || fail 'full ensure duplicated the frozen owner'
  kill -CONT -- "-$GROUP"
  wait "$caller" || fail 'full ensure did not recover with the original worker'
  printf '%s\n' "$(<"$TMP_ROOT/ensure-result")"
  wait_ready
  [ "$(<"$STATE/worker.lock/pid")" = "$original" ] || fail 'owner replaced after resume'
  job aged-heartbeat
  stop
}
binding() {
  local mtime replacement
  printf '\nSCENARIO readiness object binding: replace, unlink, recreate\n'
  start
  printf 'replacement-owner\n' > "$STATE/replacement"
  touch -t 200001010000 "$STATE/replacement"
  mv -f "$STATE/replacement" "$STATE/worker.ready"
  mtime=$(fm_remote_job_path_mtime "$STATE/worker.ready")
  /bin/sleep 2.5
  printf 'Replacement readiness: content=%s mtime-before=%s mtime-after=%s\n' "$(<"$STATE/worker.ready")" "$mtime" "$(fm_remote_job_path_mtime "$STATE/worker.ready")"
  [ "$(fm_remote_job_path_mtime "$STATE/worker.ready")" = "$mtime" ] || fail 'obsolete heartbeat refreshed replacement readiness'
  rm "$STATE/worker.ready"
  wait_ready
  [ "$(<"$STATE/worker.ready")" = "$OWNER" ] || fail 'recreated readiness names wrong owner'
  [ "$(stat -c '%a' "$STATE/worker.ready")" = 600 ] || fail 'recreated readiness is not private'
  mtime=$(fm_remote_job_path_mtime "$STATE/worker.ready")
  /bin/sleep 2.5
  printf 'Recreated readiness: owner=%s mode=%s mtime-before=%s mtime-after=%s\n' "$(<"$STATE/worker.ready")" "$(stat -c '%a' "$STATE/worker.ready")" "$mtime" "$(fm_remote_job_path_mtime "$STATE/worker.ready")"
  [ "$(fm_remote_job_path_mtime "$STATE/worker.ready")" -gt "$mtime" ] || fail 'recreated object is not refreshed'
  job readiness-recreated
  # Block the real heartbeat immediately before its no-clobber link syscall,
  # then publish a replacement to actively challenge the overwrite guard.
  : > "$GATE/link-arm"
  rm "$STATE/worker.ready"
  wait_file "$GATE/link-blocked"
  printf 'replacement-won-link-race\n' > "$STATE/worker.ready"
  touch -t 200001010000 "$STATE/worker.ready"
  replacement=$(stat -c '%i' "$STATE/worker.ready")
  # Prevent the serving loop's normal heartbeat-exit cleanup from removing
  # readiness before inspecting the link's observable no-clobber result.
  kill -STOP "$OWNER"
  : > "$GATE/link-release"
  /bin/sleep 0.25
  printf 'Contested recreation: content=%s inode-before=%s inode-after=%s mtime=%s\n' "$(<"$STATE/worker.ready")" "$replacement" "$(stat -c '%i' "$STATE/worker.ready")" "$(fm_remote_job_path_mtime "$STATE/worker.ready")"
  [ "$(<"$STATE/worker.ready")" = replacement-won-link-race ] && [ "$(stat -c '%i' "$STATE/worker.ready")" = "$replacement" ] || fail 'heartbeat clobbered contested readiness'
  kill -CONT "$OWNER"
  stop
  rm -f "$GATE/link-arm" "$GATE/link-blocked" "$GATE/link-release"
}
safety() {
  local old new mtime i
  printf '\nSCENARIO published identity mismatch: real ensure safely replaces stale-code owner\n'
  start
  old=$OWNER
  printf 'published-stale-code\n' > "$STATE/worker.identity"
  fm_remote_job_ensure_worker "$REMOTE_ROOT" "$ACCOUNT" || fail "$FM_REMOTE_JOB_ERROR"
  get_owner
  new=$OWNER
  printf 'Published mismatch: previous owner=%s current owner=%s repaired=%s\n' "$old" "$new" "$FM_REMOTE_JOB_REPAIRED"
  [ "$old" != "$new" ] || fail 'published identity mismatch did not replace owner'
  fm_remote_job_worker_identity_matches "$REMOTE_ROOT" "$ACCOUNT" || fail 'replacement identity not current'
  job published-identity-mismatch
  printf '\nSCENARIO ownership loss: heartbeat stops and readiness ages\n'
  # Freeze only the serving loop so its heartbeat observes the changed lock.
  kill -STOP "$OWNER"
  printf 'not-the-recorded-command\n' > "$STATE/worker.lock/command"
  /bin/sleep 2
  mtime=$(fm_remote_job_path_mtime "$STATE/worker.ready")
  /bin/sleep 11
  printf 'Ownership-loss readiness mtime-before=%s mtime-after=%s\n' "$mtime" "$(fm_remote_job_path_mtime "$STATE/worker.ready")"
  [ "$(fm_remote_job_path_mtime "$STATE/worker.ready")" = "$mtime" ] || fail 'heartbeat refreshed after ownership loss'
  if fm_remote_job_probe "$ACCOUNT"; then fail 'readiness stayed fresh after ownership loss'; fi
  if fm_remote_job_worker_owned_alive "$REMOTE_ROOT" "$ACCOUNT"; then fail 'mismatched owner records were accepted as owned alive'; fi
  printf 'Readiness probe and owned-alive both reject the mismatched recorded owner.\n'
  kill -CONT "$OWNER"
  stop
}
fault_injection() {
  local mtime
  printf '\nSCENARIO inode-aware touch injection: fd-based refresh is blocked and resumes on the same owner\n'
  start
  : > "$GATE/stale-arm"
  wait_file "$GATE/touch-observed"
  "$REAL_TOUCH" -t 200001010000 "$STATE/worker.ready"
  mtime=$(fm_remote_job_path_mtime "$STATE/worker.ready")
  /bin/sleep 2.5
  printf 'Inode-aware injector caught refresh target=%s; mtime-before=%s mtime-after=%s\n' "$(<"$GATE/touch-observed")" "$mtime" "$(fm_remote_job_path_mtime "$STATE/worker.ready")"
  [ "$(<"$GATE/touch-observed")" = /proc/self/fd/3 ] || fail 'real heartbeat did not use its fd-bound readiness'
  [ "$(fm_remote_job_path_mtime "$STATE/worker.ready")" = "$mtime" ] || fail 'inode-aware refresh injector failed'
  if fm_remote_job_probe "$ACCOUNT"; then fail 'blocked refresh remained ready'; fi
  fm_remote_job_lock_owner_matches_process "$ACCOUNT" || fail 'blocked refresh lost verified ownership'
  rm "$GATE/stale-arm"
  wait_ready
  job inode-aware-refresh-injection
  stop
}
printf 'Source=%s commit=%s; native platform=%s; disposable root=%s\n' "$SOURCE" "$(if [ "$SOURCE" = base ]; then printf '%s' "$BASE"; else git rev-parse HEAD; fi)" "$(uname -s)" "$REMOTE_ROOT"
case "$CASE" in
  all) initialization absent worker.pid; initialization stale worker.pid; initialization absent worker.identity; aged; binding; safety; fault_injection ;;
  aged) aged ;;
  pid) initialization absent worker.pid ;;
  identity) initialization absent worker.identity ;;
  binding) binding ;;
  *) fail "unknown scenario: $CASE" ;;
esac
printf '\nAll requested live scenarios completed successfully.\n'
