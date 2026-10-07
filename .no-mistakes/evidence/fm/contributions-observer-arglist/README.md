# Contribution diagnostics — targeted live validation

Validated target `5de80af8d7bd72aacaa70a43886ae60f6cfdc321` against base `2ce57d0067d4e860e8969fa8fa8289771b855ec5`.

## Product and isolation

The live driver executes the actual `bin/fm-contributions.sh poll`, its actual local ownership collector and record/wake libraries, and the installed **gh 2.101.0** binary. No product command is replaced. Only the dependency endpoint is disposable: a loopback TLS CONNECT server provides REST/GraphQL records, controlled response errors and latency. The server accepts only `api.github.com:443` and `github.com:443` CONNECT targets and never forwards requests to an external service. The driver uses a dummy endpoint token and separate `HOME`, `GH_CONFIG_DIR`, `FM_HOME`, state/data/config/projects directories and scratch directory inside the gate worktree. No operator records, GitHub login or credential store are used.

`live-transcript.txt` shows the CLI-visible output, stored reasons, timing and request stages. `live-transcript.json` additionally contains actual requests (without authentication headers), records before/after, per-record byte-equality observations and the wake queue. `live-scenarios.json` maps the eight scenarios to transcript entries. `live-driver.py` retains the executable driver and assertions for reproducibility.

## Live observations

- Entries 1–10: PR core, comments, reviews, inline, checks, statuses, repo and closing reads, plus issue comments and timeline events, report the proper fixed stage, numeric HTTP code and real gh exit 1. Failed waves stop before the closing read. Request logs show no retries or forge writes (POSTs are GraphQL queries).
- Entries 11–12: delayed/concurrent failures are joined in deterministic stage order; all six independent stages are exercised together as an adversarial case.
- Entries 13–14: a GraphQL error without an HTTP failure and an error whose numeric status is beyond the first 4096 bytes report HTTP status unavailable rather than fabricating it. Private response text is excluded from poll stdout/stderr and durable records in all cases.
- Entries 15–18: two owners share one read; one notification starts the episode, the repeated failure is silent, recovery clears errors, and a later outage starts a new episode. Pending signals, notification state and the saved verdict are retained, and no wake is enqueued for the already-notified signal.
- Entry 19: a changed closing head gets the fixed head-drift reason and preserves the previous observation.
- Entries 20–22: the five-second read cap, one-second configured budget, and watcher cap (`FM_CHECK_TIMEOUT=4` with requested budget 25) stop slow reads, remain silent and leave contribution record bytes unchanged.
- Entry 23: a malformed next-URL response does not inherit the preceding HTTP failure reason.
- Entry 24: the actual base-commit script replays the parallel failure, emits the old generic message and persists the old generic error, with the same seven requests and preserved observation/pending/verdict fields as the target replay.

## Focused regressions

Executed only these functions from `tests/fm-contributions.test.sh`, through a temporary runner retaining the file's helper/function definitions and replacing its final all-tests loop:

```
test_http_500_diagnostic_is_stage_only_and_keeps_pending
test_missing_or_out_of_bound_http_status_is_not_fabricated
test_diagnostic_budget_cut_keeps_record_bytes
test_head_drift_diagnostic_never_accepts_mixed_observation
test_schema_failure_does_not_inherit_http_diagnostic
test_genuine_failure_near_deadline_is_unavailable
test_shared_url_observed_once
test_unavailable_forge_records_error_and_wakes_once_per_episode
test_late_owner_keeps_failure_episode_suppressed
test_budget_is_cut_down_to_the_watcher_check_bound
```

Command: `TMPDIR="$PWD/.test-contributions-lab/tmp" bash tests/.test-contributions-focused.sh`. All passed; output is in `focused-regressions.log`. These mocked-dependency regressions are supplementary, not the basis for marking the live scenarios live. They additionally cover native exit 3, invalid/four-digit and truncated status text, deadline exhaustion mid-wave and failure near the deadline.

## Commands and setup corrections

```
mkdir -p .test-contributions-lab/tmp
openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout .test-contributions-lab/key.pem \
  -out .test-contributions-lab/cert.pem -days 1 \
  -subj '/CN=api.github.com' \
  -addext 'subjectAltName=DNS:api.github.com,DNS:github.com'
git show 2ce57d0067d4e860e8969fa8fa8289771b855ec5:bin/fm-contributions.sh \
  > bin/.test-contributions-baseline.sh
chmod +x bin/.test-contributions-baseline.sh
# live-driver.py was run from .test-contributions-lab/live.py:
python3 .test-contributions-lab/live.py
```

A preliminary `gh pr view https://github.com/o/r/pull/8 --json headRefOid,reviewDecision` probe through the same local proxy confirmed real gh TLS and GraphQL operation. The first complete live run exposed an invalid issue fixture (missing the required boolean `observation.ready`); the fixture was corrected and all scenarios were rerun successfully. A final successful rerun added before/after persisted-state evidence. This was a setup correction, not a product failure.

No full repository suite, linters, formatters, other gate phases or production lifecycle operations were run. This is a CLI diagnostics-only change; CLI transcripts and persisted JSON are the reviewer-visible surface, so no GUI screenshot is applicable. Disposable server processes, certificates/private keys, fixture homes, temporary test runner and base script were torn down; no source changes were made.
