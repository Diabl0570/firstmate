# Exact-head targeted validation

The tested committed revision is `c1a1e7da1e0037bee87ed9134eefaa559b448cb8`.
The partial staged-write repair was already committed when this turn began; there were no uncommitted repairs to adopt or commit.
Initial and final `git status --porcelain=v1` were empty.
No permanent files were changed in this turn.

## Before-fix reproduction

A disposable archive of `f7f36b01dad3670ad295e32523aca865254e7122` received only the current adapter regression file, retaining its original production code.
The command was:

```sh
git archive f7f36b01dad3670ad295e32523aca865254e7122 | tar -x -C tests/.phase-partial-before
cp tests/fm-busy-adapter-wiring.test.sh tests/.phase-partial-before/tests/fm-busy-adapter-wiring.test.sh
TMPDIR="$PWD/.phase-test/tmp" FM_TEST_SKIP_ORPHAN_REAP=1 \
  FM_TEST_ONLY=test_claude_worker_partial_settings_write_keeps_original \
  bash tests/.phase-partial-before/bin/fm-test-run.sh tests/fm-busy-adapter-wiring.test.sh
```

The regression failed as expected: it observed product exit 153 instead of the independently expected normal refusal exit 1.
`recheck-partial-before.txt` retains the failure.
The same regression passed at the committed repair head.
Core dumps were disabled for this signal-failure verification.

## Committed-head executable checks

These selections each passed through the canonical runner with no gate skip:

```sh
TMPDIR="$PWD/.phase-test/tmp" FM_TEST_SKIP_ORPHAN_REAP=1 FM_TEST_ONLY=<selection> \
  bash bin/fm-test-run.sh tests/fm-busy-adapter-wiring.test.sh
```

- `test_claude_worker_partial_settings_write_keeps_original`
- `test_claude_worker_settings_preserved`
- `test_claude_worker_invalid_settings_untouched`
- `test_claude_worker_settings_publish_failures_keep_original`
- `test_claude_hooks_semantic_lifecycle`
- `test_claude_hooks_stale_incarnation_harmless`

The existing secondmate fixture's required placement outside the source repository used the standard incidental test-toolchain temporary root, not a live session or lab:

```sh
env -u TMPDIR FM_TEST_SKIP_ORPHAN_REAP=1 FM_TEST_ONLY=<selection> \
  bash bin/fm-test-run.sh tests/fm-busy-adapter-wiring.test.sh
```

- `test_secondmate_claude_spawn_leaves_local_settings_untouched`
- `test_secondmate_claude_spawn_arms_busy_for_the_stall_gate`

The prior stall failure was not waived: its corrected fixture passed again at the committed head.
`recheck-committed-regressions.txt` retains exact commands and runner results.

Five existing relaunch cases passed individually, without running the full relaunch suite:

```sh
env -u TMPDIR FM_TEST_SKIP_ORPHAN_REAP=1 FM_TEST_ONLY=<selection> \
  bash bin/fm-test-run.sh tests/.phase-settings-relaunch.test.sh
```

- `test_relaunch_keeps_worker_local_settings_and_refreshes_only_firstmate_hooks`
- `test_malformed_worker_settings_refuse_relaunch_untouched`
- `test_failed_worker_settings_publication_refuses_relaunch_untouched`
- `test_prepublication_abort_keeps_worker_local_settings`
- `test_secondmate_claude_relaunch_keeps_local_settings`

The disposable focused driver used the committed relaunch test definitions, omitted their full-suite invocation list, selected exactly one named function with honest exit status, and used the existing shared fixture cleanup for read-only git-hook directories.
`recheck-relaunch-regressions.txt` retains the commands and results.

The preserved extra-fixture driver was copied to `.phase-test/run-extra.sh` and executed with:

```sh
TMPDIR="$PWD/.phase-test/tmp" FM_TEST_SKIP_ORPHAN_REAP=1 bash .phase-test/run-extra.sh
```

Actual spawn refused mode-000 settings while retaining original bytes and mode.
The actual focused-selector CLI rejected an unknown function with script/runner exit 1, preserved selected function exit 37 while returning runner exit 1, and succeeded for a valid existing passing selection.
`recheck-selector-and-unreadable.txt` retains those end-user CLI outputs.

## Fresh product-state evidence

```sh
bash .phase-test/observed-checks.sh
```

A disposable observer re-executed the existing preservation, publication-failure, same-task refresh/switch, malformed retirement, failed retirement publication/retry, aborted replacement, and secondmate retirement cases, retaining real product transcripts and persisted settings before and after each operation.
The observer did not change production code or assertions.
A separate partial-write fixture applied the real `ulimit -f 4` only to the product subprocess so evidence capture itself remained unrestricted.

`recheck-product-state.jsonl` shows the partial-write refusal returned 1, preserved the original settings SHA-256 `9d8f3b57d5d6eb5b6584feb1fe036e875878206dddc22662c162694e8bedae78` and mode `0640`, and left only `settings.local.json` in its directory.
The unrestricted retry returned 0, preserved saved settings semantically and retained mode `0640`.
The same artifact contains generic saved JSON, custom hook metadata, generated hook incarnations, actual retirement/refusal output, and busy-state records for the affected executable paths.
`recheck-observed-checks.txt` retains associated regression results.
`recheck-observation-driver.sh` and `recheck-capture-state.py` preserve the observation method with generic paths.

## Explicit live-proof limitation

All eight worker-settings/vendor/lifecycle live scenarios remain **NOT RUN**, `live:false`, and `result:untested`.
The synthetic executable checks above passed, but simulated transport and manually invoked hooks are not genuine vendor/session proof.
The later recorded decision withdrew live-lab authorization unused, forbade real task/session/endpoint lifecycle operations, and retained the one disclosed missing-live-proof limitation.
No lab round or real lifecycle action was attempted.
The ordinary-worker vendor launch after landing remains outstanding proof and is not authorized in this phase.
The overall live-validation verdict remains **inconclusive**, not a gate approval or a newly granted exception.
Only the outer executor may record the previously authorized acceptance reason.
The actual focused-selector CLI was driven in this turn and passed independently of this limitation.

No UI change is present; product transcripts and persisted-state evidence are the relevant surface rather than screenshots.
No complete repository suite, linter, formatter, static analyzer, pipeline-control, push, PR, CI, merge, account, configuration-propagation, or activation operation was executed.
All transient archives, drivers, fixture data, and output files created in the worktree were removed; dedicated evidence and existing dependencies were retained.
