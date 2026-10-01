#!/usr/bin/env bash
# S5: concurrent fm-on calls while a new owner initializes, starting from what an
# unclean stop plus a code update leaves behind.
# usage: s5.sh <new|base>
LAB=$(cd "$(dirname "$0")" && pwd -P); V=$1; L="$LAB/lab.sh $V"; S=$LAB/home-$V/.firstmate/remote-job
AH=$LAB/home-$V; GATE=$LAB/s5-$V.gate; HELD=$LAB/s5-$V.held; rm -f "$GATE" "$HELD"
REAL_GIT=$(readlink -f /etc/profiles/per-user/kasper/bin/git)
echo "=== S5 [$V code] concurrent fm-on calls during a new owner's initialization (after an unclean stop + code update) ==="
OLD_OWNER=$(cat $S/worker.pid); OLD_SUP=$(ps -o pgid= -p "$OLD_OWNER" | tr -d ' ')
echo "--- unclean stop: kill -KILL -$OLD_SUP (supervisor, serving process, heartbeat all die without cleanup)"; kill -KILL -- "-$OLD_SUP"; sleep 0.5
$L workers; $L state; echo "leftover lock dir: $(ls $S/worker.lock | tr '\n' ' ')"
echo "--- code update in the remote checkout"; echo "# lab code update $(date +%s)" >> $LAB/root-$V/bin/fm-remote-job-worker.sh
(cd $LAB/root-$V && git -c user.email=lab@example.invalid -c user.name=lab commit -qam "lab code update" && git log --oneline -1)
echo "--- account git wrapper (~/.local/bin/git) holds only the worker's identity hash while $GATE exists (keeps the new owner inside its initialization window)"
mkdir -p $AH/.local/bin
cat > $AH/.local/bin/git <<EOF
#!/usr/bin/env bash
if [ "\${1:-}" = hash-object ] && [ -n "\${FM_ROOT_OVERRIDE:-}" ] && [ -e "$GATE" ]; then
  printf '%s\n' "\$PPID" >> "$HELD"
  while [ -e "$GATE" ]; do sleep 0.05; done
fi
exec "$REAL_GIT" "\$@"
EOF
chmod 0755 $AH/.local/bin/git
sleep 11   # let the dead owner's readiness age past the probe bound
: > "$GATE"
rm -f $LAB/s5-$V.stop; $L sample $LAB/s5-$V.sup $LAB/s5-$V.stop & SAMPLER=$!
echo "--- call A arrives (launches the new owner)"
( SECONDS=0; timeout 100 $L entry fm-lab-echo.sh call-A; echo "call A exit=$? after ${SECONDS}s" ) > $LAB/s5-$V.a 2>&1 & A=$!
for _ in $(seq 1 200); do [ -s "$HELD" ] && break; sleep 0.05; done
[ -s "$HELD" ] && echo "new owner is held inside its initialization window" || echo "NOTE: the new owner never reached its identity hash"
sleep 0.3
echo "--- during initialization"; $L workers; $L state
NEW_LOCK_OWNER=$(cat $S/worker.lock/pid 2>/dev/null)
echo "--- call B arrives while the owner initializes"
( SECONDS=0; timeout 100 $L entry fm-lab-echo.sh call-B; echo "call B exit=$? after ${SECONDS}s" ) > $LAB/s5-$V.b 2>&1 & B=$!
sleep 4
echo "--- 4s into call B (owner still initializing)"; $L workers
echo "worker supervisors now: $($L groups | wc -l)"
echo "--- release the identity hash"; rm -f "$GATE"
wait $A; wait $B
echo "--- call transcripts"; cat $LAB/s5-$V.a $LAB/s5-$V.b
sleep 2; : > $LAB/s5-$V.stop; wait $SAMPLER
echo "--- every supervisor process seen (sampled every 50ms) from call A until 2s after both returned:"; cat $LAB/s5-$V.sup | sed 's/^/  /'
echo "supervisors seen: $(wc -l < $LAB/s5-$V.sup)  (1 = only the owner call A launched)"
echo "--- after"; $L workers; $L state
echo "initializing owner kept (worker.pid == lock owner seen during init): $([ "$NEW_LOCK_OWNER" = "$(cat $S/worker.pid 2>/dev/null)" ] && echo yes || echo "NO (init owner $NEW_LOCK_OWNER, now $(cat $S/worker.pid 2>/dev/null))")"
rm -f $AH/.local/bin/git; rmdir $AH/.local/bin $AH/.local 2>/dev/null || true
