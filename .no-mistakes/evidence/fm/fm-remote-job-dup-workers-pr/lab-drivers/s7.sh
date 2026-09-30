#!/usr/bin/env bash
# S7: the serving process crashes; the supervisor recovers and the crashed child's heartbeat does not linger.
LAB=$(cd "$(dirname "$0")" && pwd -P); V=$1; L="$LAB/lab.sh $V"; S=$LAB/home-$V/.firstmate/remote-job
echo "=== S7 [$V code] serving process crashes (SIGKILL); supervisor recovers; no stray heartbeat ==="
OLD=$(cat $S/worker.pid); SUP=$(ps -o pgid= -p $OLD | tr -d ' ')
HB=$(ps -eo pid=,ppid= | awk -v o=$OLD '$2==o {print $1}' | head -1)
echo "--- before"; $L workers; $L state; echo "heartbeat of the serving process: $HB"
echo "--- kill -KILL $OLD (serving process crashes)"; kill -KILL $OLD
for t in 1 2 3 4 5 6; do sleep 1; printf 't=%ss  ' $t; $L state | tr '\n' ' '; echo "| crashed heartbeat $HB alive: $(kill -0 $HB 2>/dev/null && echo YES || echo no)"; done
echo "--- after recovery"; $L workers
echo "--- fm-on call after recovery"; SECONDS=0; timeout 100 $L entry fm-lab-echo.sh after-crash; echo "call exit=$? after ${SECONDS}s"
echo "worker supervisors: $($L groups | wc -l) (same supervisor $SUP: $([ "$($L groups)" = "$SUP" ] && echo yes || echo no))"
echo "processes of the crashed serving process still alive: $(ps -eo pid=,ppid= | awk -v o=$OLD '$1==o || $2==o' | wc -l)"
