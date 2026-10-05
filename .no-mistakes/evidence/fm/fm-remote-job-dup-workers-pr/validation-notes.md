# Remote worker live validation

Target: `f7d2ab77594dbce136f305bfabd2b7d9c0458d2d`  
Comparison: `9ea0c41a480cf965b80bba60a80701639f70f723`

## Actual product exercised

`live-remote-worker.sh` copies the unmodified product worker, shared library and delta-read command into a disposable checkout inside the gate worktree. It starts the product's detached Linux supervisor through `fm_remote_job_start_linux_worker`, runs its serving child and independent heartbeat, and stages actual `fm-remote-delta-read.sh` jobs through the queue. Each successful serving scenario prints the persisted `done` state, exit status and real delta-read protocol response. Fixtures, worker processes and queue state are cleaned up on exit.

`live-head.log` records:

- Starts before absent/stale public PID publication and before code identity publication: verified ownership, one process group, no repair/relaunch, original owner proceeds to execute a queued command.
- Aged readiness: stale probe is rejected, repeated start creates no supervisor, full ensure waits until the original owner resumes, and that owner completes a command.
- Readiness replacement: replacement timestamp stays unchanged; removal recreates a mode-0600 ready file naming the real owner; subsequent refresh advances its timestamp and a command completes.
- Contested readiness creation: another publisher wins while the heartbeat is paused before `ln`; content, inode and old timestamp are preserved after the real no-clobber link executes.
- Published code mismatch: full ensure replaces the old owner, publishes current identity and completes a command.
- Ownership loss: changing recorded command stops refresh; readiness ages and both probe and owned-alive reject it.
- Inode-aware touch fault injection: the real heartbeat passes `/proc/self/fd/3`, the `-ef` guard catches it, readiness stays stale, and removing the injection restores service on the same owner.

Publication and link barriers are external executable fault injectors, not replacements for the product worker, queue, heartbeat or command. For contested creation the serving child is temporarily stopped to prevent normal heartbeat-failure cleanup from removing the replacement before its inode is inspected.

## Before/after reproduction

`live-base-aged.log`, `live-base-pid.log`, and `live-base-identity.log` show a second supervisor/group and `repaired=1` on the base commit. `live-base-binding.log` shows the base heartbeat refreshing a replacement readiness object it did not open. These are expected baseline failures. The corresponding target scenarios pass against the same driver.

## Host workaround and initial setup attempts

This Nix host has `sleep` on PATH but no `/bin/sleep`, which the real worker uses. The initial direct run could not reach its barrier. Validation used an unprivileged user/mount namespace with a worktree-local `/bin` overlay containing the existing bash, ps and sh links plus a link to the existing real sleep executable. No host `/bin` or global tool configuration was changed.

The first contested-link observation also raced the product's normal cleanup after a heartbeat exit. Stopping only the serving child before releasing the link barrier made the link result independently observable. The corrected complete run passed; neither setup issue required a product change. Initial attempt transcripts are retained as `initial-setup.log` and `race-observation-setup.log`.

Example complete target command, after creating that local overlay:

```sh
unshare --user --map-root-user --mount bash -c 'mount --bind "$PWD/.validation-bin" /bin && exec bash /home/kasper/.no-mistakes/evidence/01M458RD3HT76Y6NJNAFM7K96J/live-remote-worker.sh head all'
```

## Supplementary targeted automated check

`tests/fm-remote-job-launchagent.test.sh` passed under the same private `/bin` overlay with TMPDIR inside the worktree. It runs the real worker with simulated `launchctl`, including slow-sweep and stale-readiness assertions. This is supplementary automated coverage, **not** a native macOS/Aqua live check. The current host is Linux and has no `launchctl` or Aqua session; native launchd verification requires a disposable logged-in macOS account/runner.

No complete repository suite, linter, formatter, pipeline control, push, PR or CI phase was run. No product source changes were made. All worktree-local test overlays and scratch directories were removed after validation. No UI was changed or exercised; evidence is CLI protocol output, process inventory and persisted readiness state.
