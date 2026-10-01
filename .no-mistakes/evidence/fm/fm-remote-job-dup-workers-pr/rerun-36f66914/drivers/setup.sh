#!/usr/bin/env bash
# Build a disposable live lab for the Linux remote job worker and print its path.
# usage: setup.sh <worktree> <new-rev> <base-rev>
# Each variant gets its own throwaway remote checkout (AGENTS.md + bin from that
# revision, committed so the entrypoint's tracked-command check passes), its own
# throwaway account home (bound over /home/kasper inside bwrap by lab.sh entry),
# and an FM_HOME. fm-lab-echo.sh is the disposable job payload.
set -eu
WT=$1 NEW=$2 BASE=$3
DRIVERS=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
LAB=$(mktemp -d "${TMPDIR:-/tmp}/fm-rjw-lab.XXXXXX")
cp "$DRIVERS"/*.sh "$LAB/"
for V in new base; do
  rev=$NEW; [ "$V" = base ] && rev=$BASE
  mkdir -p "$LAB/root-$V" "$LAB/home-$V" "$LAB/fmhome-$V"
  git -C "$WT" archive "$rev" AGENTS.md bin | tar -x -C "$LAB/root-$V"
  cat > "$LAB/root-$V/bin/fm-lab-echo.sh" <<'SH'
#!/usr/bin/env bash
# Disposable lab job: report which worker served this call.
printf 'served "%s" by serving owner %s (job pid %s)\n' "$*" \
  "$(cat "$HOME/.firstmate/remote-job/worker.pid" 2>/dev/null || echo ?)" "$$"
printf 'lab job stderr for "%s"\n' "$*" >&2
exit 7
SH
  chmod 0755 "$LAB/root-$V/bin/fm-lab-echo.sh"
  git -C "$LAB/root-$V" init -q
  git -C "$LAB/root-$V" add -A
  git -C "$LAB/root-$V" -c user.email=lab@example.invalid -c user.name=lab \
    -c commit.gpgsign=false -c core.hooksPath=/dev/null commit -qm "lab fixture from $rev"
done
printf '%s\n' "$LAB"
