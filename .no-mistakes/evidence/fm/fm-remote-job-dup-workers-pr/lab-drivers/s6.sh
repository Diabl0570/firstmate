#!/usr/bin/env bash
# S6: a live owner running outdated code is still replaced.
LAB=$(cd "$(dirname "$0")" && pwd -P); V=$1; L="$LAB/lab.sh $V"; S=$LAB/home-$V/.firstmate/remote-job
echo "=== S6 [$V code] a live owner running outdated code is still replaced (safety guarantee kept) ==="
OLD=$(cat $S/worker.pid); OLD_SUP=$(ps -o pgid= -p $OLD | tr -d ' ')
echo "--- before"; $L workers; echo "published identity: $(cat $S/worker.identity)"
echo "--- code update in the remote checkout (worker script changes)"; echo "# lab code update $(date +%s%N)" >> $LAB/root-$V/bin/fm-remote-job-worker.sh
(cd $LAB/root-$V && git -c user.email=lab@example.invalid -c user.name=lab commit -qam "lab code update" && git log --oneline -1)
echo "current code worker hash: $(git hash-object $LAB/root-$V/bin/fm-remote-job-worker.sh)"
rm -f $LAB/s6.stop; $L sample $LAB/s6.sup $LAB/s6.stop & SAMPLER=$!
echo "--- fm-on call"; SECONDS=0; timeout 100 $L entry fm-lab-echo.sh after-update; echo "call exit=$? after ${SECONDS}s"
sleep 2; : > $LAB/s6.stop; wait $SAMPLER
echo "--- supervisors seen during the call: $(tr '\n' ' ' < $LAB/s6.sup)"
echo "--- after"; $L workers; echo "published identity: $(cat $S/worker.identity)"
echo "old owner $OLD alive: $(kill -0 $OLD 2>/dev/null && echo YES || echo no); old supervisor $OLD_SUP alive: $(kill -0 $OLD_SUP 2>/dev/null && echo YES || echo no)"
echo "worker supervisors: $($L groups | wc -l)"
