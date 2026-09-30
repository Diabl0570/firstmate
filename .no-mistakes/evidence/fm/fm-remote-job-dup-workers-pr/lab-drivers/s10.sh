#!/usr/bin/env bash
# S10: a supervisor that loses the ownership race leaves the owner's readiness, pid, identity and lock alone.
LAB=$(cd "$(dirname "$0")" && pwd -P); V=$1; L="$LAB/lab.sh $V"; S=$LAB/home-$V/.firstmate/remote-job
snap() { for f in worker.ready worker.pid worker.identity worker.lock/pid; do printf '  %-16s %s\n' "$f" "$(stat -c 'inode=%i' $S/$f 2>/dev/null || echo ABSENT) $(cat $S/$f 2>/dev/null | cut -c1-40)"; done; }
echo "=== S10 [$V code] a losing supervisor leaves the owner's readiness, pid, identity and lock in place ==="
[ -f $S/worker.pid ] || { echo "--- start an owner with an fm-on call"; timeout 60 $L entry fm-lab-echo.sh warmup; sleep 1; }
OWNER=$(cat $S/worker.pid); SUP=$(ps -o pgid= -p $OWNER | tr -d ' ')
echo "--- owner records before"; snap
echo "--- launch a second supervisor exactly as the start path does (nohup env ... fm-remote-job-worker.sh), in the lab account namespace"
SECONDS=0
bwrap --dev-bind / / --bind "$LAB/home-$V" /home/kasper --chdir / -- /run/current-system/sw/bin/env -i \
  PATH=/run/current-system/sw/bin:/etc/profiles/per-user/kasper/bin HOME=/home/kasper FM_ROOT_OVERRIDE="$LAB/root-$V" \
  FM_REMOTE_JOB_STATE_ROOT=/home/kasper/.firstmate/remote-job FM_REMOTE_JOB_PLATFORM_OVERRIDE= \
  "$LAB/root-$V/bin/fm-remote-job-worker.sh" > $LAB/s10.out 2>&1 < /dev/null
echo "losing supervisor exit=$? after ${SECONDS}s; output: $(cat $LAB/s10.out)"
echo "--- owner records after"; snap; $L state
echo "owner still serving: $(kill -0 $OWNER 2>/dev/null && echo yes || echo NO); worker supervisors: $($L groups | wc -l)"
echo "--- fm-on call"; timeout 100 $L entry fm-lab-echo.sh after-loser; echo "call exit=$?"
