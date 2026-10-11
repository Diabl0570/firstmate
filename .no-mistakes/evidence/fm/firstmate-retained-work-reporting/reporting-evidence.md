# Canonical retained-work reporting verification

The real `bin/fm-fleet-snapshot.sh` producer, its real crew-state/classification/activity owners, the home-summary publisher, and reporting consumers were executed against disposable synthetic homes.
The production scripts came from the target checkout without modification; an archived runtime and sibling fixture directories inside the worktree satisfied both the workspace boundary and the product's home-isolation guard.
The archived runtime was indexed as a disposable Git repository because `fm-on.sh` requires genuine tracked commands even for synthetic remote transport.
Git discovery was bounded so nongit fixture directories could not inherit the enclosing worktree's project identity.
Native no-mistakes results, endpoint responses, and forge responses were synthetic inputs, not substitutes for the reporting producer.
No real fleet, backend lifecycle, operator records, credentials, or native history were accessed or mutated.

## Product-output artifacts

`canonical-reporting-observations.jsonl` contains 20 sequential observations from the real producer.
Each record contains the command, fixture name, actual JSON output, wall time, exit status, and before/after SHA-256 digests of protected fixture inputs.
`canonical-repeat-observations.jsonl` independently repeats those same observations.
Only disposable absolute path prefixes have been replaced with placeholders in published output.
All protected metadata, status records, semantic records, native fixture records, backlog, report, and code inputs were unchanged across every producer invocation.

| Observation | End-user action and independent expected result |
| --- | --- |
| 1 | Read a home with failed and delivered ship attempts plus a completed scout under structured holds: retained evidence remains separate from the one active continuation, approval remains open, and landed count stays zero. |
| 2 | Read the published ledger from its parent: retained attempts, active work, and approval survive canonical aggregation. |
| 3 | Read an older compatible ledger: absent retained-attempt coverage is null, not a fabricated empty set. |
| 4 | Read malformed retained-attempt coverage: the parent reports unknown rather than healthy coverage. |
| 5 | Continue work after a failed native attempt with trusted busy evidence over a positively live endpoint: the historical failure and current activity coexist. |
| 6 | Lose the endpoint while its busy record remains: the recovery-grade positive-death verdict suppresses that active continuation, preserves failed history and holds, and grants no logical completion. |
| 7 | Make endpoint inventory unreadable, including cheap endpoint absence: activity remains unknown, never idle/dead/current work, and approval remains visible. |
| 8 | Remove the semantic activity record: native terminality does not prove inactive execution. |
| 9 | Open a keyed decision on held failed work: the terminal attempt does not answer it. |
| 10 | Stall the recovery-grade worker probe for 20 seconds with that call still open and set the existing read bound to 1 second: the producer returns unknown activity while retaining failed native history, both holds, active independent work, and the keyed call. |
| 11 | Supply incomplete native inventory while the same keyed call remains open: native coverage becomes unknown without losing the call. |
| 12 | Explicitly resolve that key: only the addressed call closes. |
| 13 | Supply a new active native run alongside older terminal history: active native work wins, rather than being hidden as retention. |
| 14 | Supply competing active native runs: the canonical result remains unknown rather than becoming a retained attempt. |
| 15 | Supply incomplete native coverage with a one-child projection cap: unknown coverage, approval, and counted retained/endpoints omissions remain visible. |
| 16 | Remove scout lifecycle evidence while keeping the report: its report alone cannot prove retention or inactivity. |
| 17 | Open a scout follow-up call while its pane/lifecycle read is unknown: the key stays open. |
| 18 | Offer rendered idle without structured lifecycle coverage: the producer does not silently normalize it as retention. |
| 19 | Supply competing live native runs while a new current keyed call remains unresolved: the canonical task row has unknown/run-step, pending_decision=true, and the open key. |
| 20 | Stall a secondmate recovery-grade probe: canonical task output returns bounded unknown activity and unknown agent liveness, retains positive cheap endpoint presence, and keeps its keyed call open. |

The repeated worker-stall observation completed in 1.511 seconds and the secondmate-stall observation completed in 1.398 seconds.
Neither timeout produced idle, dead, completed logical work, or a closed call.

`cleanup-refusal-and-preserved-work.json` contains the real refused cleanup diagnostic, retained code and head, surviving metadata/report, the still-in-flight held backlog, and a fixture tripwire showing no lifecycle mutation was attempted.
The cleanup request targeted only disposable unlanded work; no live lifecycle operation ran.

## Before-fix reproductions

`before-base-observations.jsonl` records the same first scenario driven through base producer `b675126a66fab48df49cef0a04bbe06ddc045d33`.
It fails the independent expectation with `terminal_in_flight` for the failed ship, delivered ship, and completed scout rather than separating retained evidence.

`before-pre-bound-observations.jsonl` records the scenario sequence driven through producer `d7314faa`, immediately before the read-bound correction.
Its stalled observation took 20.582 seconds and published the retained failed worker as busy after waiting for the stalled probe, instead of promptly preserving unknown coverage.
The executable elapsed-time assertion failed there and passed twice on the target producer.

## Targeted test execution

The repository runner executed `tests/fm-fleet-snapshot-view.test.sh`, `tests/fm-home-summary-refresh.test.sh`, `tests/fm-bearings-snapshot.test.sh`, and `tests/fm-secondmate-reconcile.test.sh`; all ultimately passed.
The first in-worktree fixture layout triggered the intentional home-isolation guard and inherited the enclosing Git project for nongit fixture directories.
The first archived-runtime attempts also lacked the tracked-command index needed by synthetic remote reads.
Those were setup failures: sibling fixture/runtime directories, bounded Git discovery, and a disposable runtime index fixed them without changing product code or permanent tests.
The real canonical retained-attempt scenario was then run twice with output capture, plus explicit adversarial competing-native/open-call and stalled-secondmate checks.
No full-suite walk, linter, formatter, static analysis, pipeline control, push, PR, or CI phase was executed.
This change owns a machine-readable CLI reporting surface, not rendered layout or copy placement; canonical JSON and the cleanup diagnostic are its reviewer-visible evidence rather than screenshots.
The three new commit subjects/bodies and public source/test changes were inspected and contain no direct address or private fixture identifiers.
