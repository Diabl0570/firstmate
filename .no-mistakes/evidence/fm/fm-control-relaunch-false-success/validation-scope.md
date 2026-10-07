# Relaunch false-success test evidence

## Acceptance scope

Named live Claude/Pi Herdr lab acceptance did **not** run because the guarded helper requires a literal running `default` session, which the supplied acceptance decision records as absent in this environment.
The author explicitly authorized proceeding without that live-lab acceptance.
This Test turn inspected the helper contract but did not retry provisioning, create a default/shared session, synthesize a tripwire, or start any real Herdr session.
No protected original worker was tested, stopped, replaced, or demonstrated repaired.
Portable fake-CLI and fixture-owned-process results are not real-harness lifecycle acceptance.

## Observable proof

- `classifier-before-after.log` runs the same missing-registration/process counterfactual against base `ac0811c4` and the current implementation.
  The base reports `no-agent dead husk` where independently expected behavior is `live alive refused`; the current implementation passes.
- `lifecycle-cli-fixture-transcript.log` records actual Firstmate exit/relaunch CLI outputs, transport literal writes, real fixture-owned PID state, and persisted lifecycle journals.
  Both Claude-labelled and Pi-labelled Bash originals survive unsuccessful exits without a successful replacement or injected launch command.
  Genuine fixture stops/new incarnations complete; registration-only replacements, a late live process, and false pane-death evidence refuse.
- `focused-16.log` refreshes 16 explicitly selected executable fixture functions covering registration/process classification, incarnation proofs, delivery/lifecycle agreement, typing-boundary protection, and stale-registration compatibility.
  `run-focused-16.py` documents the exact selectors and makes the selection reproducible from a worktree.
- `run-focused-lifecycle.py` repeats the four lifecycle fixtures with the product-output transcript enabled.

## Test-related repairs

Production files remain unchanged from target `68b36e65`.
Two existing test files were repaired after execution exposed fixture defects:

1. Herdr descendant fixtures now verify that a native stand-in survives its `pi` alias, falling back to a locally compiled spinner on multicall-coreutils hosts.
2. The isolated two-client fixture supplies its own `cat`/`touch` tools without admitting ambient Herdr clients.
3. The reclaim no-mutation assertion permits the newly required read-only `pane process-info` call, while still rejecting mutations.
4. Crew-state shell evidence now comes from an independent childless shell rather than the controller's rapidly changing subtree.

The initial worktree-local TMPDIR also conflicted with the existing secondmate-home isolation rule; retrying with normal test-owned temporary homes resolved that setup refusal.
An initial disposable native sleeper used while diagnosing multicall-coreutils portability was superseded by the permanent fixture repair and removed.
No process/liveness proof was weakened to make legacy tests pass.

## Execution boundary

Complete targeted scripts ultimately passed: Herdr backend, control relaunch, crew state, agy harness, lifecycle control, and portable tmux liveness.
The entire repository suite was not run.
The real-tmux compatibility check still uses stand-in processes and is not real-agent acceptance.
No linters, formatters, static analysis, pushes, PR operations, CI operations, or pipeline-control commands were run in this phase.
No screenshot was captured: this change is process/CLI lifecycle safety, and real agent TUI acceptance was expressly excluded.
All transient testing material in the worktree was removed; only intentional test-file fixes remain.
