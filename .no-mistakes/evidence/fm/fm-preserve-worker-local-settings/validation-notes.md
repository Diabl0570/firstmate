# Targeted settings validation

## Evidence scope

All settings/lifecycle checks use the real Firstmate scripts with disposable generic git/task homes and stubbed session transports.
They are executable synthetic regressions, not live Claude or fleet-session proofs.
The recorded authorization forbids operating real tasks/endpoints; no real worker, credential store, default tmux server, or Herdr session was operated.

The JSONL artifacts retain product CLI output, persisted settings, file modes, and SHA-256 values captured before fixture cleanup.
Paths in copied content are normalized to `<code-root>` and `<fixture>`; SHA-256 values refer to the original fixture bytes before that normalization.

## Atomic publication observations

`test_claude_worker_settings_publish_failures_keep_original` exercised staging, staged-write, and replacement failures, then successful retries.
Each refusal left the saved settings hash unchanged and mode `0640`; initial creation used mode `0644` under umask `022`.

| Failure | Prior and post-refusal SHA-256 | Retained mode |
| --- | --- | --- |
| staging | `e2cdf2a83a4600cb3e773521993220c301ff24202fc7b2ce6716b36db57a2866` | `0640` |
| staged write | `16aecd579990daf64594b2f88a47c25ba22cf35fbc5c9990e38df564df330542` | `0640` |
| replacement | `ad53e9f5a22a37395b27c95b356875a5621eba0e9534f8da7faba3f2d7bbb346` | `0640` |

The product emitted `could not stage refreshed Claude worker hooks` or `could not publish refreshed Claude worker hooks ...; left it unchanged`.
The executable regressions also required no staged file to remain and checked that retry replaced only generated hooks.
The retirement-path publication failure preserved mode `0600` and identical prior/post-refusal bytes, refused to arm a replacement, and then succeeded on retry.

The same publication-failure regression was run against a disposable source snapshot of the pre-atomic commit `4c35ce27`.
Its stage-failure case failed because the old updater proceeded to `spawned worker-publish-stage-refresh ...` and returned 0 rather than refusing with 1.
This is a before/after regression check, not a simulated disk-exhaustion proof.

## Same-task retirement and refusal observations

The same task `rl44` was replaced twice on Claude, retaining permissions, environment, nested fields, ordinary hooks, and the worker hook added to a generated group.
Each replacement generated a new incarnation; the old generation was absent from the persisted settings.
Executing the newly generated submit and Stop commands drove the actual busy-state writer.
Switching the same task to Codex left exactly the worker-owned settings.
An aborted prepublication replacement also left worker settings and custom hooks while removing generated commands.

Malformed settings were refused on installation and retirement without changing the existing bytes.
A separate executable fixture made a valid worker settings file mode `000`; the product reported `Permission denied` and refused the refresh.
The fixture verified unchanged mode before restoring readability solely to compare the original bytes.

## Previously failing stall regression

The focused secondmate stall check failed both at the target and in a disposable base-commit snapshot with `a secondmate inside an armed turn published a durable stall notification`.
The retained queue showed the actual reason was `secondmate sm-claude auto-relaunch failed after confirmed agent absence on existing endpoint`, not a busy/idle stall notification.
Its test transport returned `0` for the foreground command, so it did not model the running agent the case required.

The only permanent Test-phase edit makes that fixture answer `claude` for the foreground-command query and asserts the actual backend liveness consumer returns `alive` before running the watcher.
No runtime stall, supervision, account, permission, or propagation behavior was changed and no existing assertion was removed.
Both the canonical focused rerun and the evidence-producing rerun passed: the frozen row stayed quiet while busy, and after Stop the product emitted `secondmate wake-loop stalled: mate=sm-claude row=7 idle=3s`.
Pre-fix and post-fix queue/busy-state artifacts are retained separately.

## Limits

An evidence attempt placed the synthetic secondmate home under the worktree and hit the existing `secondmate home cannot be inside the firstmate repo` refusal.
That setup was corrected by using the test toolchain's disposable temporary-directory placement and re-driving the scenario; the setup refusal is not treated as a product failure.
No full repository suite, linter, formatter, static-analysis tool, push, PR, or CI phase was run.
Temporary drivers selected only existing relevant relaunch functions and collected persisted product output before cleanup; they were removed afterward.
The public focused-selector CLI was driven with an unknown selection, an injected selected function returning 37, and a valid passing selection; its transcript is retained separately.
