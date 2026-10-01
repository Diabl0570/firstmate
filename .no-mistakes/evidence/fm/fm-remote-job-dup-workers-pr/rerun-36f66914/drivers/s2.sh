#!/usr/bin/env bash
# S2: a burst of concurrent fm-on calls against a live owner never adds a supervisor.
# usage: s2.sh <new|base> [calls]
LAB=$(cd "$(dirname "$0")" && pwd -P); V=$1; N=${2:-12}; L="$LAB/lab.sh $V"; S=$LAB/home-$V/.firstmate/remote-job
echo "=== S2 [$V code] $N concurrent fm-on calls against a live owner ==="
OWNER=$(cat "$S/worker.pid"); SUP=$(ps -o pgid= -p "$OWNER" | tr -d ' ')
rm -f "$LAB/s2-$V.stop"; $L sample "$LAB/s2-$V.sup" "$LAB/s2-$V.stop" & SAMPLER=$!
SECONDS=0
for i in $(seq 1 "$N"); do
  ( timeout 100 $L entry fm-lab-echo.sh "call-$i" > "$LAB/s2-$V.$i.out" 2>/dev/null; echo $? > "$LAB/s2-$V.$i.rc" ) &
done
wait $(jobs -p | grep -vx "$SAMPLER")
echo "all calls returned after ${SECONDS}s"
served=0
for i in $(seq 1 "$N"); do
  rc=$(cat "$LAB/s2-$V.$i.rc"); out=$(cat "$LAB/s2-$V.$i.out")
  [ "$rc" = 7 ] && case "$out" in *"call-$i"*"$OWNER"*) served=$((served + 1)) ;; esac
  echo "  call-$i exit=$rc $out"
done
sleep 1; : > "$LAB/s2-$V.stop"; wait "$SAMPLER"
echo "served by the existing owner: $served/$N"
echo "supervisors seen during the burst (50ms sampling): $(tr '\n' ' ' < "$LAB/s2-$V.sup")(owner's supervisor: $SUP)"
echo "owner unchanged: $([ "$OWNER" = "$(cat "$S/worker.pid")" ] && echo yes || echo NO)"
$L workers
