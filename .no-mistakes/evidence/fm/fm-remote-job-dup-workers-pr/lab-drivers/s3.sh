#!/usr/bin/env bash
# S3: a live, verified lock owner whose heartbeat aged on a starved host.
# usage: s3.sh <new|base>
LAB=$(cd "$(dirname "$0")" && pwd -P); V=$1; L="$LAB/lab.sh $V"; S=$LAB/home-$V/.firstmate/remote-job
echo "=== S3 [$V code] loaded host: owner frozen until its heartbeat ages past the probe bound, then an fm-on call arrives ==="
[ -f "$S/worker.pid" ] || { timeout 60 $L entry fm-lab-echo.sh warmup; }
sleep 1
OWNER=$(cat $S/worker.pid); G=$(ps -o pgid= -p "$OWNER" | tr -d ' ')
echo "--- steady state"; $L workers; $L state
echo "--- kill -STOP -$G  (freeze the whole owner tree, as a starved host would)"; kill -STOP -- "-$G"
sleep 12
echo "--- after 12s frozen"; $L state
( . $LAB/root-$V/bin/fm-remote-job-lib.sh; FM_REMOTE_JOB_STATE_ROOT=$S; fm_remote_job_probe $LAB/home-$V && echo "probe: fresh" || echo "probe: STALE (owner still holds the verified lock: pid/start/command match)" )
rm -f $LAB/s3-$V.stop; $L sample $LAB/s3-$V.sup $LAB/s3-$V.stop & SAMPLER=$!
echo "--- fm-on call arrives while the owner is starved"
( SECONDS=0; timeout 100 $L entry fm-lab-echo.sh during-starvation; echo "call exit=$? after ${SECONDS}s" ) > $LAB/s3-$V.call 2>&1 &
CALL=$!
sleep 4
echo "--- 4s into the call (owner still frozen)"; $L workers
echo "worker supervisors now: $($L groups | wc -l)"
echo "--- kill -CONT -$G  (load subsides)"; kill -CONT -- "-$G"
wait $CALL
echo "--- call transcript"; cat $LAB/s3-$V.call
sleep 3
: > $LAB/s3-$V.stop; wait $SAMPLER
echo "--- every supervisor process seen (sampled every 50ms) from the call until 3s after it returned:"; while read -r p; do [ "$p" = "$G" ] && echo "  $p (the owner's own supervisor)" || echo "  $p EXTRA supervisor launched beside the live owner"; done < $LAB/s3-$V.sup
echo "supervisors seen: $(wc -l < $LAB/s3-$V.sup)"
echo "--- after the call"; $L workers; $L state
echo "worker supervisors: $($L groups | wc -l)"
echo "owner unchanged: $([ "$OWNER" = "$(cat $S/worker.pid 2>/dev/null)" ] && echo yes || echo "NO (now $(cat $S/worker.pid 2>/dev/null))")"
echo "--- worker log"; tail -20 $S/logs/*.log
