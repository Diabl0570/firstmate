# Live validation at 36f66914: never duplicate a live remote job worker owner

This round re-ran every scenario against target `36f66914`, compared with the rebased base `549e07f3`. The files one
level up are from an earlier round against the pre-rebase base `eb77f02`.

Every call ran the real `bin/fm-remote-entrypoint.sh`, the same command `fm-on.sh` runs over SSH. Each call started the
real Linux worker from a throwaway remote checkout (`AGENTS.md` and `bin/` from that revision, committed). The account
home was a throwaway directory bound over `/home/kasper` inside a bubblewrap mount namespace, so the real home was never
visible. The worker state is the default `~/.firstmate/remote-job` inside that home. A disposable `fm-lab-echo.sh` job
(exit 7 on purpose) reported which serving owner served each call. A 50 ms sampler recorded every supervisor process seen
during each call. The drivers are in `drivers/`: `setup.sh` builds the lab, and `lab.sh` runs the entrypoint and lists
workers. The lab was removed afterward, and no lab process is left.

| Scenario | This change (36f66914) | Base (549e07f3) |
| --- | --- | --- |
| S1 cold start through the entrypoint | 1 supervisor, serving owner and heartbeat process; both calls served by the same owner | 1 supervisor, no heartbeat process; served |
| S2 12 concurrent calls against a live owner | 12/12 served by the existing owner; only its supervisor seen | - |
| S3 whole owner tree frozen until its heartbeat is 12s old (probe stale), then a call | only the owner's supervisor seen; call served after resume; owner unchanged | **extra supervisor 2991554 launched** beside the live owner |
| S4 only the serving process stalled for ~18s | readiness age stays 1s, probe fresh, only the owner's supervisor seen | readiness ages to 14s, probe stale, **extra supervisor 2984218 launched** |
| S5 calls during a new owner's initialization, after an unclean stop and a code update | stale pid, identity and readiness cleared; call B launched nothing; both calls served by the initializing owner | stale pid, identity and 12s-old readiness visible during init; **extra supervisor 3018658 launched** |
| S6 live owner on outdated code | replaced (old supervisor and owner gone), new identity published, 1 supervisor | - |
| S7 serving process SIGKILLed | heartbeat of the crashed child gone within 1s; same supervisor restarts; call served | - |
| S8 crash with the supervisor stopped (zombie child answers kill -0) | heartbeat stops, readiness ages past 10s, probe stale; a call is served by one fresh owner; the delayed supervisor exits on resume | - |
| S9 SIGTERM stop, and pruned checkout | 0 processes left (supervisor, serving, heartbeat); lock, pid, identity and readiness released | - |
| S10 losing supervisor beside a live owner: (a) defers, (b) cannot verify the owner | (a) exits 0, (b) exits 1; owner's readiness, pid, identity and lock keep the same inode and content | same records kept (readiness inode changes only because base rewrites it each second) |

`fm-remote-job.test.log` is `tests/fm-remote-job.test.sh` at 36f66914, run inside bubblewrap with `/usr/bin` and `/bin`
overlaid by `/run/current-system/sw/bin`, because this NixOS host has no coreutils there. Result: 43 ok, ALL TESTS
PASSED, including the 7 new scenario tests and upstream's dispatcher cadence cases.
