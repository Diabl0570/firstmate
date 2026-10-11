# Focused partial-write repair validation

## Committed and tested revision

- Before-fix product revision: `f7f36b01dad3670ad295e32523aca865254e7122`.
- Committed and tested repair: `c1a1e7da1e0037bee87ed9134eefaa559b448cb8`.
- Commit subject: `Clean staged settings after interrupted writes`.
- Files: `bin/fm-spawn.sh`, `tests/fm-busy-adapter-wiring.test.sh`.
- Final `git status --porcelain=v1`: empty, including untracked files.

The existing Test-owned diff was preserved and committed without unrelated changes.
The defect is a SIGXFSZ interruption of the shell builtin that writes staged settings: the parent updater died before reaching its existing failure cleanup.
Running only that write in a subshell contains the signal, lets the parent refuse publication and remove partial output, and leaves saved settings and permission metadata intact.
The regression uses a real `ulimit -f 4`, checks the normal refusal, unchanged original bytes and mode, absence of staging residue, and a successful unrestricted retry.

## Reproduction

A disposable in-worktree archive of the before-fix revision received only the current regression test file, leaving its production code unchanged.

```sh
git archive f7f36b01dad3670ad295e32523aca865254e7122 | tar -x -C tests/.partial-before-product
cp tests/fm-busy-adapter-wiring.test.sh tests/.partial-before-product/tests/fm-busy-adapter-wiring.test.sh
TMPDIR="$PWD/.phase-test/tmp" FM_TEST_SKIP_ORPHAN_REAP=1 \
  FM_TEST_ONLY=test_claude_worker_partial_settings_write_keeps_original \
  bash tests/.partial-before-product/bin/fm-test-run.sh tests/fm-busy-adapter-wiring.test.sh
```

Result: runner exit 1; the regression observed product exit 153 instead of its independently expected normal refusal exit 1.
The same focused regression passed with the preserved correction before commitment and again at the committed repair revision.
The full before-fix failure output is retained in `partial-write-repair-command-output.txt` with the private workspace prefix replaced by `<worktree>`.

## Committed-head focused executable checks

For each of these selections, the exact command form was:

```sh
TMPDIR="$PWD/.phase-test/tmp" FM_TEST_SKIP_ORPHAN_REAP=1 \
  FM_TEST_ONLY=<selection> \
  bash bin/fm-test-run.sh tests/fm-busy-adapter-wiring.test.sh
```

Each passed with runner/script exit 0 and no gate skip:

- `test_claude_worker_partial_settings_write_keeps_original`
- `test_claude_worker_settings_preserved`
- `test_claude_worker_invalid_settings_untouched`
- `test_claude_worker_settings_publish_failures_keep_original`
- `test_claude_hooks_semantic_lifecycle`
- `test_claude_hooks_stale_incarnation_harmless`

These two selections passed using the canonical fixture toolchain's standard ephemeral temp root:

```sh
env -u TMPDIR FM_TEST_SKIP_ORPHAN_REAP=1 FM_TEST_ONLY=<selection> \
  bash bin/fm-test-run.sh tests/fm-busy-adapter-wiring.test.sh
```

- `test_secondmate_claude_spawn_leaves_local_settings_untouched`
- `test_secondmate_claude_spawn_arms_busy_for_the_stall_gate`

An initial attempt to place the secondmate fixture under the repository correctly hit the product's existing refusal that a secondmate home cannot be inside the Firstmate repository.
This was a fixture-placement/setup issue, not a settings defect; retrying with standard incidental test-toolchain temp files passed without product or assertion changes.
No live session or vendor was launched.

Five existing relaunch tests were run individually through the canonical runner using a disposable focused driver containing the committed test definitions, not the full script's invocation list.
The driver's only additional behavior was selecting the requested function with honest exit status and using the shared read-only-directory-safe fixture cleanup.
Its command form was:

```sh
env -u TMPDIR FM_TEST_SKIP_ORPHAN_REAP=1 FM_TEST_ONLY=<selection> \
  bash bin/fm-test-run.sh tests/.settings-relaunch-focused.test.sh
```

All passed with runner/script exit 0 and no gate skip:

- `test_relaunch_keeps_worker_local_settings_and_refreshes_only_firstmate_hooks`
- `test_malformed_worker_settings_refuse_relaunch_untouched`
- `test_failed_worker_settings_publication_refuses_relaunch_untouched`
- `test_prepublication_abort_keeps_worker_local_settings`
- `test_secondmate_claude_relaunch_keeps_local_settings`

These execute the actual control, retirement, settings updater, generated hook commands and busy-state interfaces, with simulated session transports.
They verify same-task replacement and switching, malformed retirement refusal, failed retirement publication and retry, aborted-replacement cleanup, and secondmate settings isolation.

Additional executable fixture and selector commands are preserved in `partial-write-repair-extra-fixtures.sh`.
They were run via:

```sh
TMPDIR="$PWD/.phase-test/tmp" FM_TEST_SKIP_ORPHAN_REAP=1 bash .phase-test/run-extra.sh
```

- A mode-000 settings fixture passed: actual spawn refused it, its mode stayed 000, and its bytes were unchanged when reopened for comparison.
- Unknown focused function: runner/script exit 1, as expected.
- Exported selected function returning 37: script exit 37, runner exit 1, as expected.
- Valid existing stale-incarnation selection: runner/script exit 0, as expected.

## Evidence scope and remaining limitation

All eight worker-settings/vendor/lifecycle live scenarios remain **NOT RUN**, `live:false`, with live validation **inconclusive**:

1. Ordinary-worker hook installation or refresh with saved settings and custom hook metadata.
2. Same-worker relaunch with replacement of only generated hook incarnations.
3. Switching away from Claude while retaining worker settings.
4. Aborted replacement retirement with settings preservation.
5. Malformed or unreadable settings refusal without changing bytes or permissions.
6. Staging, writing and publication failure safety.
7. Vendor-invoked refreshed busy/idle hooks and stale-incarnation rejection.
8. Secondmate-local settings preservation during spawn and relaunch.

The executable fixtures passed but simulated session transport is not genuine vendor/session evidence.
Live-lab validation was withdrawn unused; no lab round, real task, endpoint or session lifecycle action was attempted.
First ordinary-worker vendor proof after landing remains outstanding and is not authorized here.
This report does not approve the Test gate or record an acceptance exception; only the outer executor may handle the already disclosed missing-live-proof exception.

The actual focused-selector CLI was exercised successfully, independently of those worker-live limitations.
No complete suite, linter, formatter, static analyzer, pipeline-control, push, PR, CI, merge or activation command was run.
All disposable archives, drivers, fixture outputs and in-worktree temporary data created for this phase were removed; no dependencies were removed.
Prior fixes and evidence were retained.
