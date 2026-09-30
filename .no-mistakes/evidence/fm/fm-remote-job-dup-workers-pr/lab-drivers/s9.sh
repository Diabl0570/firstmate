#!/usr/bin/env bash
# S9: stopping a worker never leaves the heartbeat process behind.
LAB=$(cd "$(dirname "$0")" && pwd -P); V=$1; L="$LAB/lab.sh $V"; S=$LAB/home-$V/.firstmate/remote-job
leftovers() { # <pids...>
  local p n=0; for p in "$@"; do kill -0 $p 2>/dev/null && { n=$((n+1)); ps -o pid=,stat=,args= -p $p; }; done; echo "still-alive processes of the stopped tree: $n"
}
tree_pids() { ps -eo pid=,pgid= | awk -v g=$1 '$2==g {print $1}'; }
echo "=== S9 [$V code] stopping the worker never leaves a stray heartbeat ==="
echo "--- (a) SIGTERM to the supervisor (normal service stop)"
OWNER=$(cat $S/worker.pid); SUP=$(ps -o pgid= -p $OWNER | tr -d ' '); PIDS=$(tree_pids $SUP)
$L workers
kill -TERM $SUP; sleep 3
leftovers $PIDS; $L state; echo "lock released: $([ -e $S/worker.lock ] && echo NO || echo yes)"
echo "--- restart with an fm-on call"; timeout 100 $L entry fm-lab-echo.sh restart; echo "call exit=$?"; sleep 1
echo "--- (b) the configured checkout is pruned (AGENTS.md removed): the worker abandons itself"
OWNER=$(cat $S/worker.pid); SUP=$(ps -o pgid= -p $OWNER | tr -d ' '); PIDS=$(tree_pids $SUP)
$L workers
mv $LAB/root-$V/AGENTS.md $LAB/root-$V/AGENTS.md.pruned
for _ in $(seq 1 60); do [ -z "$(tree_pids $SUP)" ] && break; sleep 0.25; done
leftovers $PIDS; $L state; echo "lock released: $([ -e $S/worker.lock ] && echo NO || echo yes)"
echo "worker log:"; tail -3 $S/logs/*.log
mv $LAB/root-$V/AGENTS.md.pruned $LAB/root-$V/AGENTS.md
