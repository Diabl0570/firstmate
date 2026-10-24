# Retained-work and endpoint-bound validation

Target: 720ab533aeca9f094c3b530dcd9ba77aea6d55f7
Base: d22640f478e3392313e27b04fb41de12bd25d2e7

## Real product runs

`live-snapshot-transcript.log` records real `bin/fm-fleet-snapshot.sh` invocations, with an actual Claude CLI in a 120-column by 40-row private tmux session. No default tmux server or Herdr session was used. Claude remained at workspace trust: this proves process liveness, not a logged-in model turn. Backlog rows, report content and semantic events are deliberately disposable input records; the events are written through the real `fm-busy-event.sh` interface, not through a substitute snapshot implementation.

The live snapshots demonstrate:

- A completed scout under a captain hold remains logical `in_flight`, is retained, keeps its approval, and is not landed.
- Removing its structured hold yields invalid `terminal_in_flight` (the producer's invalid summary can still carry its diagnostic best-effort state; `valid` and `invalidity` are the trust boundary).
- A semantic busy event remains current work despite historical report delivery.
- Missing and generation-mismatched semantic records stay unknown without answering an open call.
- A positively missing endpoint overrides an old busy record as dead.

For the stalled endpoint checks the driver SIGSTOPs only the owned private tmux server, observes actual blocked tmux client processes below each snapshot invocation, then SIGCONTs the server in `finally`. The native, Perl-only-PATH and forced-Bash mechanisms all return unknown current state, null endpoint existence, endpoint-unverified activity, and an open decision. `live-endpoint-process-evidence.json` records actual PID/parent/group/command observations and no remaining live descendants. Elapsed times are diagnostic single-trial deadline checks, not a benchmark or speedup claim. No zero-sized PTY was used.

The native and Bash runner changes are also covered by the focused nested-bound test with TERM-resistant descendant processes; the same test fails against the base timeout library and passes against the target.

## Actual parent ledger consumer

`parent-current-ledger.json`, `parent-legacy-ledger.json`, and `parent-malformed-ledger.json` were emitted by the real parent snapshot CLI with the normal installed-tool PATH, no parent task metadata, and disposable persisted home-summary ledger input. The existing retention test supplied those disposable records. Its child native-run production uses mocked upstream commands and is NOT credited as live native-run validation; the parent only consumes the persisted ledger, so no upstream native-run service is required for these parent-consumer scenarios. The current ledger preserves retained native/scout attempts and approvals, the legacy ledger leaves retained coverage null, and malformed retained coverage becomes unknown.

## Focused checks and regression comparison

- `TMPDIR="$PWD/.validation-tmp" FM_TEST_SKIP_ORPHAN_REAP=1 /bin/bash tests/fm-timeout-lib.test.sh` passed.
- The first snapshot test invocation under that TMPDIR correctly hit the existing safety boundary rejecting a secondmate home inside the source root. This was test setup, not a product regression.
- Copied the unchanged `bin/` and `tests/` to `.validation-tmp/deployment/`, with fixture TMPDIR `.validation-tmp/fixtures/` beside it, then ran `/bin/bash .validation-tmp/deployment/tests/fm-fleet-snapshot-view.test.sh`; all focused assertions passed.
- In the disposable deployment only, replaced `fm-timeout-lib.sh` with its base-commit version and ran the target timeout tests: failed with `native inner runner orphaned its descendant after the outer bound`. Restored the target library.
- In the disposable deployment only, replaced `fm-fleet-snapshot.sh` with its base-commit version and ran the target snapshot tests: failed with retained-attempt/current-work misclassification. Restored the target script.
- For the parent evidence run, the disposable test copy used the normal PATH instead of its parent fakebin, saved the three parent JSON outputs, and ran only its retention scenario. Assertions passed. `parent-consumer-driver.test.sh` preserves this exact disposable test driver.
- Ran the live driver after correcting its initial numeric tmux target to the exact recorded window name. Its isolated Perl PATH initially omitted `find`; added a link to the installed real executable and required empty stderr on the final run. All final live assertions passed.

No source, committed tests, agent memory, dependencies or tool configuration were changed. No linter, formatter, static analyzer, full repository suite, pipeline-control command, push or PR command was run. Private tmux servers and lab homes were stopped/removed within their evidence-producing command. The disposable deployment and driver staging directory are removed before returning this phase.

## Remaining live boundary

Failed/completed *native no-mistakes run* retention, native same-task continuation, and the associated unlanded cleanup refusal passed the focused executable tests with disposable mocked native protocol input. They are not credited as live native lifecycle validation. This phase is explicitly forbidden to initialize, start or control another no-mistakes run, and it must not use the operator's existing native state. Providing a pre-existing terminal native run in a disposable project/home to a future test invocation would enable that additional integration proof without relaxing the phase boundary. No native producer or run-attribution code changed in this patch; the changed projections are exercised through focused protocol-input checks and the actual persisted-ledger consumer.

## Evidence drivers

To reproduce in another authorized worktree, stage `live-snapshot-driver.sh` as `.validation-tmp/live-snapshot.sh` and `live-bounded-endpoint-driver.py` as `.validation-tmp/live-bounded-endpoint.py`, create `.validation-tmp/`, and run `bash .validation-tmp/live-snapshot.sh`. The scripts write to this run's explicit evidence directory. They use a short worktree-local `l.XXXXXX` lab name to keep the private Unix socket below its path-length limit. Do not point them at a production home or shared tmux socket.

This is a CLI/JSON change, not a rendered UI change; CLI transcripts and serialized product outputs are the reviewer-visible evidence rather than screenshots.
