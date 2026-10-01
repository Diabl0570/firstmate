#!/usr/bin/env bash
# S1: cold start through the real entrypoint, then a second call reuses the owner.
# usage: s1.sh <new|base>
LAB=$(cd "$(dirname "$0")" && pwd -P); V=$1; L="$LAB/lab.sh $V"; S=$LAB/home-$V/.firstmate/remote-job
echo "=== S1 [$V code] cold start: an fm-on call through fm-remote-entrypoint.sh starts one worker and is served ==="
echo "--- state before: $(ls -A "$LAB/home-$V" | tr '\n' ' ')(empty account home)"
SECONDS=0
timeout 100 $L entry fm-lab-echo.sh first call > "$LAB/s1-$V.out" 2> "$LAB/s1-$V.err"
echo "call 1 exit=$? after ${SECONDS}s (the job exits 7 on purpose)"
echo "  stdout: $(cat "$LAB/s1-$V.out")"; echo "  stderr: $(cat "$LAB/s1-$V.err")"
sleep 1.5
echo "--- workers after call 1"; $L workers; $L state
OWNER=$(cat "$S/worker.pid")
SECONDS=0
timeout 100 $L entry fm-lab-echo.sh second call > "$LAB/s1-$V.out" 2> "$LAB/s1-$V.err"
echo "call 2 exit=$? after ${SECONDS}s"
echo "  stdout: $(cat "$LAB/s1-$V.out")"; echo "  stderr: $(cat "$LAB/s1-$V.err")"
echo "--- workers after call 2"; $L workers; $L state
echo "worker supervisors: $($L groups | wc -l); owner reused: $([ "$OWNER" = "$(cat "$S/worker.pid")" ] && echo yes || echo NO)"
