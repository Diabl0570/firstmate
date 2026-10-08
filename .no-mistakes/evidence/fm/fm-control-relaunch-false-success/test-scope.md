# Relaunch safety test evidence

Target: `ea2e3e0969ba4b109a458bce471e13d1e2ee2e65`.
Baseline: `3c58ec8e0123b0047f9bf319e0edd5788eec988d`.

## Executed checks

- `env TMPDIR="$PWD/.test-phase-tmp" FM_TEST_EVIDENCE=1 bash bin/fm-test-run.sh --jobs 1 --json <evidence>/focused-timing.json tests/fm-backend-herdr.test.sh tests/fm-control-relaunch.test.sh tests/fm-control.test.sh tests/fm-crew-state.test.sh tests/fm-herdr-session-cleanup.test.sh tests/fm-agy-harness.test.sh`
- `env TMPDIR=/tmp FM_TEST_EVIDENCE=1 bash bin/fm-test-run.sh --jobs 1 --json <evidence>/relaunch-rerun-timing.json tests/fm-control-relaunch.test.sh`
- An instrumented temporary driver re-executed the existing `test_herdr_missing_registration_never_relaunches_a_surviving_original`, `test_herdr_relaunch_requires_real_stop_and_replacement_incarnation`, `test_herdr_relaunch_rechecks_the_shell_at_the_typing_boundary`, and `test_herdr_stop_postcondition_cannot_borrow_a_false_dead_read` functions.
  The driver preserved their assertions and logged actual Firstmate CLI output, fixture-owned PID/start values, independent original-PID re-reads, journals, delivery inboxes, and fake transport payloads.
  Its final output is `lifecycle-fixture-transcript.txt`; all four functions passed again.
- The baseline adapter was extracted with `git archive <baseline> bin` into a disposable directory inside the worktree.
  A deterministic registration/process counterfactual executed both baseline and target classifiers with the same supplied evidence and independently asserted expected results.
  `registration-before-after.txt` shows the baseline wrongly permitting recovery for missing registration plus live/foreign/unreadable process evidence, and the target preserving liveness or refusing.

## Setup correction

The first suite invocation placed temporary fixtures under the repository.
Five suites passed, but the relaunch suite stopped at its secondmate-home test because the product correctly forbids secondmate homes inside the Firstmate repository.
The unchanged relaunch suite was rerun using the toolchain's ordinary temporary location, and completed successfully including all new Herdr lifecycle fixtures.
This was a test-location error, not a production regression; both receipts are retained.
No source or permanent test changes were made.

## Acceptance limit

All liveness and lifecycle evidence here is portable fixture evidence, not real-harness acceptance.
The process fixtures are renamed Bash processes; Herdr transport and registration reads are faked.
The named live Claude/Pi Herdr lab acceptance did NOT run because the recorded helper prerequisite requires a literal live default session that was absent in the earlier refusal.
The author explicitly accepted proceeding without that acceptance and prohibited retrying provisioning, starting/reconfiguring the default session, or bypassing the helper/tripwire.
This turn did not retry that refusal or launch any real Herdr session or Claude/Pi runtime.
The accepted 0/8 actual Claude/Pi acceptance limitation remains unchanged.
No protected original worker was inspected, stopped, relaunched, or certified repaired.
There is no screenshot because no real agent TUI was launched under that restriction; the change is lifecycle/CLI safety rather than visual layout or copy placement.

Only targeted executable checks were run; no full repository suite, lint, formatting, static analysis, publication, PR, or CI action was performed.
Temporary drivers, the extracted baseline, and test residue inside the worktree were removed after collecting these receipts.
