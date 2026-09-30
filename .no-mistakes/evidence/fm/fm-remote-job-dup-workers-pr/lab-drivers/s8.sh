#!/usr/bin/env bash
# S8: the serving process crashes while its supervisor is delayed (child unreaped, a zombie that still answers kill -0).
LAB=$(cd "$(dirname "$0")" && pwd -P); V=$1; L="$LAB/lab.sh $V"; S=$LAB/home-$V/.firstmate/remote-job
echo "=== S8 [$V code] crash with a delayed supervisor: heartbeat must stop so readiness ages; fm-on still gets served ==="
OLD=$(cat $S/worker.pid); SUP=$(ps -o pgid= -p $OLD | tr -d ' ')
HB=$(ps -eo pid=,ppid= | awk -v o=$OLD '$2==o {print $1}' | head -1)
echo "--- before"; $L workers; $L state
echo "--- kill -STOP $SUP (supervisor delayed), kill -KILL $OLD (serving process crashes, stays unreaped)"; kill -STOP $SUP; kill -KILL $OLD
sleep 0.5; echo "serving process state: $(ps -o stat= -p $OLD)  (Z = zombie, still answers kill -0: $(kill -0 $OLD 2>/dev/null && echo yes || echo no))"
for t in 2 4 6 8 10 12; do sleep 2; printf 't=%2ss  ' $t; $L state | tail -1 | tr '\n' ' '; echo "| heartbeat $HB alive: $(kill -0 $HB 2>/dev/null && echo YES || echo no)"; done
( . $LAB/root-$V/bin/fm-remote-job-lib.sh; FM_REMOTE_JOB_STATE_ROOT=$S; fm_remote_job_probe $LAB/home-$V && echo "probe: FRESH (a dead worker would read as ready)" || echo "probe: stale (the dead worker does not read as ready)" )
echo "--- fm-on call while the crashed child is still unreaped"; SECONDS=0; timeout 100 $L entry fm-lab-echo.sh during-delayed-recovery; echo "call exit=$? after ${SECONDS}s"
$L workers; $L state
echo "--- kill -CONT $SUP (delayed supervisor resumes)"; kill -CONT $SUP; sleep 4
$L workers; $L state
echo "worker supervisors: $($L groups | wc -l); delayed supervisor $SUP alive: $(kill -0 $SUP 2>/dev/null && echo yes || echo no)"
echo "--- fm-on call after"; timeout 100 $L entry fm-lab-echo.sh after; echo "call exit=$?"
