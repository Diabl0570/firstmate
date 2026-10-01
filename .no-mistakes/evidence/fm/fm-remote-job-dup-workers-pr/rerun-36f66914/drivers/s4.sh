#!/usr/bin/env bash
# S4: a serving pass stalls (only the serving process stops); the heartbeat must stay fresh.
# usage: s4.sh <new|base>
LAB=$(cd "$(dirname "$0")" && pwd -P); V=$1; L="$LAB/lab.sh $V"; S=$LAB/home-$V/.firstmate/remote-job
echo "=== S4 [$V code] slow serving pass: only the serving process stalls for ~18s while fm-on calls arrive ==="
OWNER=$(cat $S/worker.pid); SUP=$(ps -o pgid= -p "$OWNER" | tr -d ' ')
echo "--- steady state"; $L workers; $L state
echo "--- kill -STOP $OWNER  (serving process only; supervisor and any heartbeat process keep running)"; kill -STOP "$OWNER"
for t in 2 4 6 8 10 12 14; do sleep 2; printf 't=%2ss  ' "$t"; $L state | tail -1; done
( . $LAB/root-$V/bin/fm-remote-job-lib.sh; FM_REMOTE_JOB_STATE_ROOT=$S; fm_remote_job_probe $LAB/home-$V && echo "probe at t=14s: fresh" || echo "probe at t=14s: STALE" )
rm -f $LAB/s4-$V.stop; $L sample $LAB/s4-$V.sup $LAB/s4-$V.stop & SAMPLER=$!
echo "--- fm-on call arrives during the stalled pass"
( SECONDS=0; timeout 100 $L entry fm-lab-echo.sh during-slow-pass; echo "call exit=$? after ${SECONDS}s" ) > $LAB/s4-$V.call 2>&1 &
CALL=$!
sleep 4
echo "--- 4s into the call (pass still stalled)"; $L workers
echo "--- kill -CONT $OWNER  (the pass returns)"; kill -CONT "$OWNER"
wait $CALL
echo "--- call transcript"; cat $LAB/s4-$V.call
sleep 3; : > $LAB/s4-$V.stop; wait $SAMPLER
echo "--- every supervisor process seen (sampled every 50ms) from the call until 3s after it returned:"; while read -r p; do [ "$p" = "$SUP" ] && echo "  $p (the owner's own supervisor)" || echo "  $p EXTRA supervisor launched beside the live owner"; done < $LAB/s4-$V.sup
echo "supervisors seen: $(wc -l < $LAB/s4-$V.sup)"
echo "--- after"; $L workers; $L state
echo "owner unchanged: $([ "$OWNER" = "$(cat $S/worker.pid 2>/dev/null)" ] && echo yes || echo "NO (now $(cat $S/worker.pid 2>/dev/null))")"
