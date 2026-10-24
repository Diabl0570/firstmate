# Owned-contribution observation validation

Target: `798fd553f20e1c875f46d93689918e4ce63d848b`
Baseline: `29c3e867b369de8532704e0b54ac988d239a668a`

## Result

The real contribution CLI and installed GitHub CLI passed the live scenarios against a disposable loopback TLS forge. The targeted existing contribution regression script also passed. No source changes were required.

The forge supplies disposable external records and injected HTTP failures, not replacements for Firstmate or `gh`. All Firstmate snapshot, enrollment, polling, retry, pending, acknowledgement, verdict, persistence, and notification code executes unmodified. GitHub HTTPS requests terminate at the loopback server using an ephemeral CA and dummy token. No production GitHub request, operator home, login, fleet, or credential store is used. These checks prove the local product/real-CLI integration, not GitHub service availability.

## Product-level evidence

- `live-contributions.log`: actual CLI commands, stdout/stderr, and persisted public `fm-contributions.v1` records.
- `coherent-observation.json`: a paginated maintainer comment, successful checks, closing-head verification, optional review-thread read, both owners' durable pending signals, and one durable notification.
- `acknowledged-observation.json`: acknowledgement removes only one owner's pending token; the other owner retains its signal and an explicit exact-head maintainer verdict.
- `transient-recovered.json`: the actual forge request log shows one retry for each initially failing independent read, successful observation, and retained pending/verdict evidence.
- `parallel-both.json` / `parallel-reverse.json`: differently ordered concurrent failures yield the same sorted checks/statuses diagnostic; previous observation, pending signals, acknowledgements, and verdict are retained. Repeated outage polling is silent; successful polling clears the error; a later outage reports a new episode.
- `bounded-oversized.json`, `bounded-invalid-http.json`, and `bounded-cut-http.json`: oversized/truncated stderr yields a fixed fallback; invalid `HTTP 5000` body text does not fabricate HTTP 500. Real gh correctly reports the actual HTTP 422 when its transport suffix fits inside the bound. Private sentinel/endpoint/header-like body text is absent from target stdout, stderr, and durable diagnostics.
- `head-drift.json`: changed closing head produces the fixed drift reason and retains the previous coherent observation.
- `budget-refusal.json`: server saw the core request but no closing-head request; a deadline kill remains silent and preserves the exact prior durable record bytes. The driver checks this by byte comparison, not a timestamp proxy.
- `schema-isolation.json`: after a reviews HTTP 404, a malformed second URL reports only its own structural validation failure.
- `ready-issue.json`: issue comments and timeline reads still produce a durable ready-for-pr signal.
- `baseline-reproduced.json`: the same local transport against the base revision reproduces raw private-text retention and omission of another parallel failing stage. Target assertions reject both behaviors.
- `drive-contributions.py`: reproducible standalone driver; run from the worktree with `python3 /home/kasper/.no-mistakes/evidence/01M5P95G6JPG8XSVC4A4MC2XBY/drive-contributions.py`. It creates/removes `.test-validation/live` and a temporary baseline script under `bin/` within its own run. No tool installation is necessary.

## Targeted existing regressions and setup correction

Ran only `tests/fm-contributions.test.sh`, not the repository-wide suite, linters, static analysis, or remote CI.

1. Initial command: `TMPDIR="$PWD/.test-validation/tmp" FM_TEST_SKIP_ORPHAN_REAP=1 bash tests/fm-contributions.test.sh`. Observer-specific regressions passed, but three cross-home checks failed because placing their fixture homes under the repository intentionally violates the real secondmate-home validator's ancestor boundary. This is a fixture-location problem, not an observer failure. The original output is retained as `contribution-regressions.log`.
2. Corrected command: `TMPDIR=/tmp FM_TEST_SKIP_ORPHAN_REAP=1 bash tests/fm-contributions.test.sh`. The test toolchain's ordinary self-cleaning ephemeral fixtures are permitted by the workspace boundary. The whole targeted script passed, including those cross-home checks and all added diagnostics/deadline regressions. Output is `contribution-regressions-default-temp.log`, with `EXIT_STATUS=0 ELAPSED_SECONDS=214`.

The corrected regression runtime is one local end-to-end script measurement, not a performance improvement or a projection of full CI time. This script deliberately includes server-delay/timeout scenarios and repeated observations; its successful output confirms these paths actually ran rather than being skipped. The initial location-invalid run took 210 seconds. Neither value establishes remote loaded-shard headroom; the existing CI configuration and its budget are unchanged, and the outer executor owns CI validation.

The first live-driver attempt also corrected an expectation in the disposable driver: real gh appends the true HTTP 422 transport status to a short invalid-status body. Expecting a status-free fallback there was incorrect; the final driver expects the actual 422 while rejecting a fabricated 500. The fully corrected live driver passed on repeat.

## Cleanup and scope

All local forge processes, TLS material, disposable homes, and temporary baseline scripts are removed by the driver. The test library cleans its ephemeral regression fixtures. Remaining worktree-only test scratch is removed before returning. Published evidence remains in this evidence directory. The changed surface is CLI-only, so transcripts and persisted protocol records are the reviewer-visible artifacts; there is no rendered UI to capture.
