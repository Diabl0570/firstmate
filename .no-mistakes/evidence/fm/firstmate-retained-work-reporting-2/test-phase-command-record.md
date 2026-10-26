# Targeted Test rerun

Validated HEAD: `292c9f05b8f82e91caba053fa61791b444412f0c`
Compared against: `ffb2aca0546ca8f540df67ed41c227a30e22d2f0`

Only shipped automated tests and fixtures were executed. No source, tests, assertions, timeouts, or configuration files were edited. No linter, formatter, full-suite run, real agent CLI, network request, or pipeline-control command was run. Prior-turn artifacts already in this evidence directory were not used as evidence of this rerun.

## Commands and results

Each test command below was executed inside `bash -o pipefail -c`, with `2>&1 | tee <log>` appended. The wrapper captured `${PIPESTATUS[0]}`, printed `COMMAND_EXIT=<status>`, and returned that status; tee therefore did not conceal a failed test.

| Exact test invocation | Test/wrapper exit | Log in this directory | Result |
| --- | --- | --- | --- |
| `TMPDIR="$PWD/.test-tmp" /bin/bash tests/fm-timeout-lib.test.sh` | 0 | `timeout-library.log` | Passed: mechanism selection, stdin bytes, streams/status/cwd/caller state, refusal without a runner, signals, ownership, and two-level nested cancellation. The gtimeout case routes through a shipped shim invoking the available GNU timeout; this is not a native BSD gtimeout proof. |
| `TMPDIR="$PWD/.test-tmp" /bin/bash tests/fm-fleet-snapshot-view.test.sh` | 1 | `retained-work-reporting.log` | Setup failure: secondmate fixture was inside the repository, so the real consumer rejected it with `invalid home: secondmate home cannot be inside the firstmate repo`. No assertion or product change was made. |
| `/bin/bash tests/fm-fleet-snapshot-view.test.sh` | 0 | `retained-work-reporting-default-temp.log` | Passed using shipped default temporary location. Exercised retained/current separation, busy continuation, unknown/ambiguous activity, endpoint loss/stalls, open calls, legacy ledgers, and refusal to remove unlanded work. |
| `/bin/bash bin/fm-test-run.sh tests/fm-home-summary-refresh.test.sh tests/fm-fleet-snapshot-contribution-input.test.sh` | 0 (both scripts 0) | `summary-refresh-and-contribution.log` | Passed: real summary producer/writer/watcher/consumer with fixture external dependencies, atomic publication, bounded failure paths and assembly error propagation. |
| `/bin/bash tests/fm-supervision-host.test.sh` | 1 | `supervision-host.log` | Ran the shipped simulated-session suite unchanged. Stopped at `test_tagged_lock_holder_reaches_the_engine_whole`; the subsequent `test_superseded_host_leaves_the_owner_untouched` did not execute. |
| `/bin/bash bin/fm-test-run.sh tests/fm-crew-state.test.sh` | 0 (script 0) | `crew-state.log` | Passed: native-read fixtures, run attribution, ambiguous/incomplete coverage, current activity, terminal delivery, and decision/state reconciliation. |

The timeout/snapshot pair and, later, the supervision/crew-state pair ran concurrently. No thresholds were changed.

## Supervision isolation blocker

Observed failure:

```text
not ok - tagged: the host never started a watcher cycle: supervision-host stood down: this session does not own supervision
COMMAND_EXIT=1
```

`tests/fm-supervision-host.test.sh:3174` defines the Windows-tagged-holder case. Its shipped `ps` fixture handles only `ps -W` and delegates other questions to `/bin/ps`. Unlike ordinary cases, it launches the host under plain bash rather than the test's fake Claude session. Consequently the real agent ancestry remains visible. `fm_harness_ancestry_pids` prefers a discovered POSIX harness over the Windows fallback, so that simulated `win:7204` lock does not establish ownership here. The safe refusal happens before a watcher is armed. The case offers no shipped selector or supported isolation switch to hide that ancestry. No process-tree workaround, fixture rewrite, skipped assertion, or real-agent launch was attempted. Re-run the unchanged suite from a non-agent runner, or separately authorize a fixture-isolation repair; this run does not establish a product ownership defect.

## Coverage boundaries

All behavioral results are fixture-based, not live-agent proof. The real shell interfaces run, but native no-mistakes, terminal endpoints, and/or the supervision engine are supplied by shipped fakes. No new harness was written or run. The accepted three-nested-Perl cancellation limitation was not redesigned or claimed fixed; the timeout suite's nested regressions cover two bounds, not the full refresh/snapshot/native-query cancellation chain. No real-model or network scenario was run because the operator explicitly forbade it. No screenshot or rendered UI artifact was collected: this rerun is limited to shell/JSON interfaces and shipped test fixtures.

## Cleanup and final checks

Read-only inspection used `git diff --stat`, targeted `git diff`, `git status --porcelain=v1 --untracked-files=all`, file reads, and bounded repository searches. One inspection `rg` invocation named nonexistent `bin/fm-session-lock.sh` and `bin/fm-claude-stop-hook.sh`; it reported those missing paths, and inspection continued using the repository's actual `bin/fm-session-lock-lib.sh` and `bin/fm-claude-stop-autoarm.sh`. No test depended on those guessed paths.

Final command sequence:

```sh
git diff --exit-code
git status --porcelain=v1 --untracked-files=all
git ls-files -- .test-tmp/
rmdir .test-tmp
git status --porcelain=v1 --untracked-files=all
git diff --quiet
printf 'FINAL_CHECK_EXIT=%s\n' "$?"
```

All checks exited 0, both status outputs were empty, and no tracked files existed under `.test-tmp/`. Shipped cleanup had already removed its test-generated contents; `rmdir` removed only the remaining empty scratch directory. No other project path was removed. Final output: `FINAL_CHECK_EXIT=0`.
