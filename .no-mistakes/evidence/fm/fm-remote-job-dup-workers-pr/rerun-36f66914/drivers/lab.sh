#!/usr/bin/env bash
# Disposable live lab for the Linux remote job worker.
# usage: lab.sh <new|base> <subcommand> [args...]
#   entry <fm-cmd> [args...]  run the real fm-remote-entrypoint.sh exactly as sshd
#                             would, inside a bwrap mount namespace whose
#                             /home/kasper is this variant's throwaway account home
#   workers                   list this variant's worker processes with roles
#   groups                    print the distinct worker process groups
#   state                     show owner records and readiness age
set -u
LAB=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
V=$1; shift
ROOT=$LAB/root-$V
AHOME=$LAB/home-$V
FMH=$LAB/fmhome-$V
STATE=$AHOME/.firstmate/remote-job
WORKER="$ROOT/bin/fm-remote-job-worker.sh"
SYS_PATH=/run/current-system/sw/bin:/etc/profiles/per-user/kasper/bin

b64() { printf '%s' "$1" | base64 -w0; }

entry() {
  local argv
  argv=$(printf '%s\0' "$@" | base64 -w0)
  bwrap --dev-bind / / --bind "$AHOME" /home/kasper --chdir / -- \
    /run/current-system/sw/bin/env -i PATH="$SYS_PATH" HOME=/home/kasper USER=kasper LOGNAME=kasper \
    "$ROOT/bin/fm-remote-entrypoint.sh" 1 "$(b64 "$ROOT")" "$(b64 "$FMH")" "$argv" < /dev/null
}

worker_rows() { # pid ppid pgid stat etimes kind (kind: supervisor|--serve|--lane)
  ps -eo pid=,ppid=,pgid=,stat=,etimes=,args= | awk -v w="$WORKER" '{
    cmd=""; kind="supervisor"
    for (i=6;i<=NF;i++) { cmd=cmd (i>6?" ":"") $i; if ($i==w && i<NF) kind=$(i+1) }
    if (index(cmd, w) > 0 && $6 !~ /awk$/) print $1, $2, $3, $4, $5, kind
  }'
}

workers() {
  local owner lock_owner pid ppid pgid stat et role
  owner=$(cat "$STATE/worker.pid" 2>/dev/null || true)
  lock_owner=$(cat "$STATE/worker.lock/pid" 2>/dev/null || true)
  printf '%-8s %-8s %-8s %-5s %-6s %s\n' PID PPID PGID STAT AGE ROLE
  while read -r pid ppid pgid stat et kind; do
    if [ "$kind" = supervisor ]; then role=supervisor
    elif [ "$pid" = "$owner" ] || [ "$pid" = "$lock_owner" ]; then role="serving-owner (--serve)"
    elif [ "$kind" = --serve ] && [ "$ppid" = "$owner" ]; then role="heartbeat of owner (--serve subshell)"
    elif [ "$kind" = --serve ]; then role="other --serve process"
    else role="job lane ($kind)"
    fi
    printf '%-8s %-8s %-8s %-5s %-6s %s\n' "$pid" "$ppid" "$pgid" "$stat" "${et}s" "$role"
  done < <(worker_rows)
}

groups() { worker_rows | awk '$6 == "supervisor" {print $3}' | sort -u; }

# Every 50ms until <stop-file> appears, records each distinct supervisor
# (a worker process started without --serve/--lane) ever seen.
sample() { # <out> <stop-file>
  : > "$1"
  while [ ! -e "$2" ]; do
    worker_rows | awk '$6 == "supervisor" { print $1 }' >> "$1.raw"
    sleep 0.05
  done
  sort -u "$1.raw" > "$1"; rm -f "$1.raw"
}

state() {
  local now mtime
  now=$(date +%s)
  printf 'worker.lock/pid=%s worker.pid=%s identity=%s\n' \
    "$(cat "$STATE/worker.lock/pid" 2>/dev/null || echo -)" \
    "$(cat "$STATE/worker.pid" 2>/dev/null || echo -)" \
    "$(cut -c1-20 "$STATE/worker.identity" 2>/dev/null || echo -)"
  if [ -f "$STATE/worker.ready" ]; then
    mtime=$(stat -c %Y "$STATE/worker.ready")
    printf 'worker.ready age=%ss (probe bound 10s)\n' "$((now - mtime))"
  else
    printf 'worker.ready absent\n'
  fi
}

"$@"
