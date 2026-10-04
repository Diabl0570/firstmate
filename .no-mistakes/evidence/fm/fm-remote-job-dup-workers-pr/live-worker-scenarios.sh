#!/usr/bin/env bash
# Live product driver: real worker scripts, processes, queue, and tracked delta command.
set -eu
CODE=$1
CASE=$2
EVIDENCE=$3
ACCOUNT="$CASE/account"
REMOTE_HOME="$CASE/home"
STATE="$CASE/state"
GATE="$CASE/gate"
OWNER=
GROUP=
REAL_TOUCH=$(command -v touch)
REAL_LN=$(command -v ln)
mkdir -p "$ACCOUNT/.local/bin" "$REMOTE_HOME/state" "$GATE"
export HOME="$ACCOUNT" FM_HOME="$REMOTE_HOME" FM_ROOT_OVERRIDE="$CODE"
export FM_REMOTE_JOB_STATE_ROOT="$STATE" FM_REMOTE_JOB_PLATFORM_OVERRIDE=Linux
export FM_REMOTE_JOB_QUEUE_TIMEOUT=30 FM_REMOTE_JOB_TIMEOUT=15
export FM_LIVE_GATE="$GATE" FM_LIVE_STATE="$STATE" FM_LIVE_TOUCH="$REAL_TOUCH" FM_LIVE_LN="$REAL_LN"
unset FM_STATE_OVERRIDE FM_DATA_OVERRIDE FM_CONFIG_OVERRIDE FM_PROJECTS_OVERRIDE FM_REMOTE_JOB_ACTIVE
. "$CODE/bin/fm-remote-job-lib.sh"
cleanup() {
  : > "$GATE/release-touch"
  : > "$GATE/release-ln"
  if [ -n "$GROUP" ]; then kill -CONT -- "-$GROUP" 2>/dev/null || true; fi
  if [ -n "$OWNER" ]; then fm_remote_job_stop_worker_tree "$OWNER" || true; fi
  # Only process groups whose exact script argument is this disposable code root.
  for pg in $(ps -eo pgid=,args= | awk -v w="$CODE/bin/fm-remote-job-worker.sh" '$3 == w {print $1}' | sort -u); do
    kill -CONT -- "-$pg" 2>/dev/null || true
    kill -TERM -- "-$pg" 2>/dev/null || true
  done
}
trap cleanup EXIT
wait_file() {
  for _ in $(seq 1 200); do [ -f "$1" ] && return 0; sleep 0.05; done
  printf 'FAIL: missing %s\n' "$1" >&2; return 1
}
wait_fresh() {
  for _ in $(seq 1 200); do fm_remote_job_probe "$ACCOUNT" && return 0; sleep 0.05; done
  printf 'FAIL: readiness never became fresh\n' >&2; return 1
}
start() {
  fm_remote_job_ensure_worker "$CODE" "$ACCOUNT"
  OWNER=$(cat "$STATE/worker.pid")
  GROUP=$(fm_remote_job_process_pgid "$OWNER")
  printf 'Worker ready: owner=%s group=%s inode=%s mode=%s\n' "$OWNER" "$GROUP" "$(stat -c %i "$STATE/worker.ready")" "$(stat -c %a "$STATE/worker.ready")"
}
processes() { ps -eo pid=,ppid=,pgid=,state=,args= | awk -v w="$CODE/bin/fm-remote-job-worker.sh" '$6 == w'; }
stop() {
  kill -CONT -- "-$GROUP" 2>/dev/null || true
  fm_remote_job_stop_worker_tree "$OWNER"
  OWNER= GROUP=
}
start
printf '\nSCENARIO: concurrent starts reuse a verified owner with stale readiness\n'
processes
kill -STOP -- "-$GROUP"
sleep 0.2
"$REAL_TOUCH" -t 200001010000 "$STATE/worker.ready"
! fm_remote_job_probe "$ACCOUNT"
fm_remote_job_lock_owner_matches_process "$ACCOUNT"
printf 'Aged ready mtime=%s; verified lock owner=%s\n' "$(stat -c %Y "$STATE/worker.ready")" "$FM_REMOTE_JOB_OWNER_PID"
FM_REMOTE_JOB_REPAIRED=0
fm_remote_job_start_linux_worker "$CODE" "$ACCOUNT"
printf 'First concurrent start: repaired=%s lock-owner=%s\n' "$FM_REMOTE_JOB_REPAIRED" "$(cat "$STATE/worker.lock/pid")"
processes
[ "$FM_REMOTE_JOB_REPAIRED" = 0 ] || { printf 'FAIL: a second supervisor was launched beside the live owner\n'; exit 1; }
START_PIDS=()
for _ in 1 2 3; do
  (FM_REMOTE_JOB_REPAIRED=0; fm_remote_job_start_linux_worker "$CODE" "$ACCOUNT"; printf 'Concurrent start repaired=%s\n' "$FM_REMOTE_JOB_REPAIRED"; [ "$FM_REMOTE_JOB_REPAIRED" = 0 ]) &
  START_PIDS+=("$!")
done
for start_pid in "${START_PIDS[@]}"; do wait "$start_pid"; done
[ "$(processes | awk '{print $3}' | sort -u)" = "$GROUP" ]
kill -CONT -- "-$GROUP"
wait_fresh
fm_remote_job_ensure_worker "$CODE" "$ACCOUNT"
[ "$(cat "$STATE/worker.pid")" = "$OWNER" ]
printf 'PASS: all starts retained owner=%s and one supervisor group=%s\n' "$OWNER" "$GROUP"

printf '\nSCENARIO: resumed original worker completes a real tracked command\n'
printf 'live-ready-again\n' > "$REMOTE_HOME/state/live.log"
EMPTY_HASH=$(printf '' | sha256sum | awk '{print $1}')
fm_remote_job_stage "$ACCOUNT" "$CODE" "$REMOTE_HOME" fm-remote-delta-read.sh state/live.log 0 "$EMPTY_HASH" 1 </dev/null >/dev/null
JOB=$FM_REMOTE_JOB_ID
fm_remote_job_wait "$ACCOUNT" "$JOB"
printf 'Job %s exit=%s, output follows:\n' "$JOB" "$FM_REMOTE_JOB_EXIT"
cat "$FM_REMOTE_JOB_STDOUT"
[ "$FM_REMOTE_JOB_EXIT" = 0 ]
grep -Fx 'live-ready-again' "$FM_REMOTE_JOB_STDOUT"
cp "$FM_REMOTE_JOB_STDOUT" "$EVIDENCE/live-job-response.txt"
fm_remote_job_reap "$ACCOUNT" "$JOB"
printf 'PASS: command result was returned by the original owner=%s\n' "$OWNER"
stop

# Instrument OS touch and ln boundaries; never replace the product worker.
cat > "$ACCOUNT/.local/bin/touch" <<'WRAPPER'
#!/usr/bin/env bash
set -eu
last=${!#}
if [ -f "$FM_LIVE_GATE/block-touch" ] && [ "$last" -ef "$FM_LIVE_STATE/worker.ready" ] && mkdir "$FM_LIVE_GATE/touch-claimed" 2>/dev/null; then
  printf 'Refresh reached OS boundary: pid=%s path=%s inode=%s\n' "$$" "$last" "$(stat -c %i -L "$last")" > "$FM_LIVE_GATE/touch-observed"
  while [ ! -f "$FM_LIVE_GATE/release-touch" ]; do /bin/sleep 0.05; done
fi
exec "$FM_LIVE_TOUCH" "$@"
WRAPPER
cat > "$ACCOUNT/.local/bin/ln" <<'WRAPPER'
#!/usr/bin/env bash
set -eu
last=${!#}
if [ -f "$FM_LIVE_GATE/block-ln" ] && [ "$last" = "$FM_LIVE_STATE/worker.ready" ] && mkdir "$FM_LIVE_GATE/ln-claimed" 2>/dev/null; then
  printf 'Recreate reached OS boundary: pid=%s destination=%s\n' "$$" "$last" > "$FM_LIVE_GATE/ln-observed"
  while [ ! -f "$FM_LIVE_GATE/release-ln" ]; do /bin/sleep 0.05; done
fi
exec "$FM_LIVE_LN" "$@"
WRAPPER
chmod +x "$ACCOUNT/.local/bin/touch" "$ACCOUNT/.local/bin/ln"
export PATH="$ACCOUNT/.local/bin:$PATH"
start
printf '\nSCENARIO: delayed old refresh cannot mutate replacement readiness\n'
: > "$GATE/block-touch"
wait_file "$GATE/touch-observed"
cat "$GATE/touch-observed"
"$REAL_LN" "$STATE/worker.ready" "$STATE/ready-original-link"
"$REAL_TOUCH" -t 200001010000 "$STATE/ready-original-link"
printf 'replacement-owner\n' > "$STATE/.replacement"
"$REAL_TOUCH" -t 200001010000 "$STATE/.replacement"
mv -f "$STATE/.replacement" "$STATE/worker.ready"
# Break recorded ownership after the old refresh passed the real owner check.
cp "$STATE/worker.lock/command" "$STATE/owner-command.saved"
printf 'ownership-lost\n' > "$STATE/worker.lock/command"
REPLACEMENT_BEFORE=$(stat -c %Y "$STATE/worker.ready")
: > "$GATE/release-touch"
sleep 2.5
printf 'Old object mtime=%s; replacement mtime=%s; replacement contents=%s\n' "$(stat -c %Y "$STATE/ready-original-link")" "$(stat -c %Y "$STATE/worker.ready")" "$(cat "$STATE/worker.ready")"
[ "$(stat -c %Y "$STATE/worker.ready")" = "$REPLACEMENT_BEFORE" ]
[ "$(cat "$STATE/worker.ready")" = replacement-owner ]
[ "$(stat -c %Y "$STATE/ready-original-link")" -gt "$REPLACEMENT_BEFORE" ]
printf 'PASS: the delayed refresh reached only its original object\n'
# Restore only this lab's owner metadata so normal safe stop can release its lock.
cp "$STATE/owner-command.saved" "$STATE/worker.lock/command"
stop
rm -f "$GATE/block-touch"
start
printf '\nSCENARIO: missing readiness is recreated and refreshed with owner PID and mode 0600\n'
rm -f "$STATE/worker.ready"
wait_fresh
[ "$(cat "$STATE/worker.ready")" = "$OWNER" ]
[ "$(stat -c %a "$STATE/worker.ready")" = 600 ]
RECREATED_INODE=$(stat -c %i "$STATE/worker.ready")
RECREATED_TIME=$(stat -c %Y "$STATE/worker.ready")
sleep 2.5
printf 'Recreated inode=%s owner=%s mode=%s mtime=%s -> %s\n' "$RECREATED_INODE" "$(cat "$STATE/worker.ready")" "$(stat -c %a "$STATE/worker.ready")" "$RECREATED_TIME" "$(stat -c %Y "$STATE/worker.ready")"
[ "$(stat -c %i "$STATE/worker.ready")" = "$RECREATED_INODE" ]
[ "$(stat -c %Y "$STATE/worker.ready")" -gt "$RECREATED_TIME" ]
printf 'PASS: recreated readiness stays fresh on its bound object\n'

printf '\nSCENARIO: racing publication cannot be overwritten by readiness recreation\n'
: > "$GATE/block-ln"
rm -f "$STATE/worker.ready"
wait_file "$GATE/ln-observed"
cat "$GATE/ln-observed"
printf 'racing-owner\n' > "$STATE/.racing"
"$REAL_TOUCH" -t 200001010000 "$STATE/.racing"
mv -f "$STATE/.racing" "$STATE/worker.ready"
RACING_INODE=$(stat -c %i "$STATE/worker.ready")
RACING_MTIME=$(stat -c %Y "$STATE/worker.ready")
# Delay serving recovery so the no-clobber heartbeat mutation is independently observable.
kill -STOP "$OWNER"
: > "$GATE/release-ln"
sleep 2
printf 'Racing object inode=%s contents=%s mtime=%s\n' "$(stat -c %i "$STATE/worker.ready")" "$(cat "$STATE/worker.ready")" "$(stat -c %Y "$STATE/worker.ready")"
[ "$(stat -c %i "$STATE/worker.ready")" = "$RACING_INODE" ]
[ "$(stat -c %Y "$STATE/worker.ready")" = "$RACING_MTIME" ]
[ "$(cat "$STATE/worker.ready")" = racing-owner ]
printf 'PASS: no-clobber recreation preserved the racing readiness publication\n'
stop
rm -f "$GATE/block-ln"
start
printf '\nSCENARIO: ownership loss stops readiness refresh\n'
printf 'ownership-lost\n' > "$STATE/worker.lock/command"
sleep 2
LOST_TIME=$(stat -c %Y "$STATE/worker.ready")
sleep 11
printf 'Ownership-lost readiness mtime=%s -> %s, age=%ss\n' "$LOST_TIME" "$(stat -c %Y "$STATE/worker.ready")" "$(( $(date +%s) - LOST_TIME ))"
[ "$(stat -c %Y "$STATE/worker.ready")" = "$LOST_TIME" ]
! fm_remote_job_probe "$ACCOUNT"
printf 'PASS: readiness expired after ownership loss\n'
stop
printf '\nALL LIVE SCENARIOS PASSED\n'
