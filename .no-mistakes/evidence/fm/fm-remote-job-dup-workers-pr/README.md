# Live validation: never duplicate a live remote job worker owner

Every scenario ran the real `bin/fm-remote-entrypoint.sh`, the same command `fm-on.sh` runs over SSH. Each call started the real
Linux worker from a throwaway remote checkout. The account home was a throwaway directory, mounted over `$HOME` inside a
bubblewrap mount namespace so the real home was never visible. A disposable `fm-lab-echo.sh` job reported which worker
served each call. Driver scripts are in `lab-drivers/`. The lab has been removed.

"base" means the same lab running `bin/fm-remote-job-lib.sh` and `bin/fm-remote-job-worker.sh` from eb77f02, before
this change.

| Scenario | This change | Base (eb77f02) |
| --- | --- | --- |
| S1 cold start through the entrypoint | 1 supervisor, serving owner and heartbeat process; job served | - |
| S2 12 concurrent calls against a live owner | 12/12 served, 1 supervisor, owner unchanged | - |
| S3 whole owner tree frozen until its heartbeat is 12-13s old, then a call | 1 supervisor seen; call served after resume | **extra supervisor launched** beside the live owner |
| S4 only the serving process stalled for 18s | heartbeat age stays 0s, probe fresh, 1 supervisor | heartbeat ages to 15s, probe stale, **extra supervisor launched** |
| S5 calls during a new owner's initialization, after an unclean stop and a code update | stale pid, identity and readiness cleared; 1 supervisor; owner kept | stale records visible during init; **extra supervisor launched** |
| S6 live owner on outdated code | replaced (old tree gone), new identity, 1 supervisor | - |
| S7 serving process SIGKILLed | heartbeat of the crashed child exits within 1s; same supervisor restarts it; call served | - |
| S8 crash with the supervisor delayed (zombie child) | heartbeat stops, readiness ages past 10s, call served by one fresh owner, delayed supervisor exits | - |
| S9 SIGTERM stop and pruned checkout | 0 processes left (supervisor, serving, heartbeat); lock, pid, identity and readiness released | - |
| S10 losing supervisor started beside a live owner | exits 0; owner's readiness, pid, identity and lock keep the same inode and content | - |

`fm-remote-job.test.log`: `tests/fm-remote-job.test.sh` run inside bubblewrap with an FHS `/usr/bin` overlay, since
this NixOS host has no coreutils under `/usr/bin`. Result: ALL TESTS PASSED.
