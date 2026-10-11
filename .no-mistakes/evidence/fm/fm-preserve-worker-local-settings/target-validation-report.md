# Targeted settings validation

## Scope and current result

The inspected target was f7f36b01dad3670ad295e32523aca865254e7122.
Targeted executable settings regressions passed, including the corrected secondmate stall fixture.
A further real partial-write failure was reproduced and corrected in this Test turn.
The focused selector was exercised through the actual canonical runner, without replacing the runner or selector.
The overall live verdict remains inconclusive: no real worker or lab endpoint was started in this turn.
The settings proofs use the real Firstmate scripts against disposable synthetic homes with stubbed session transports, and are not live worker proofs.

## Partial staged-write reproduction and correction

A disposable ordinary-worker fixture had saved permissions, environment, and a large generic JSON field.
The original settings fit below the process's 4 KiB output limit; the merged hook settings did not.
At the target, a real `ulimit -f 4` killed the in-process staged `printf` with SIGXFSZ (product exit 153), leaving an incomplete `.settings.local.json.*` file beside the original.
The original settings remained intact, but the required staging cleanup and normal publication refusal did not run.
An initial observation attempt accidentally applied the same output limit to the evidence observer; that instrumentation problem was corrected by restricting the limit to the product subprocess, then the failure was independently reproduced.

The Test correction runs only the staged `printf` in a subshell, so its signal becomes a failed write status that the existing updater cleanup handles.
No settings owner, hook semantics, permission policy, account behavior, or configuration propagation was changed.
A permanent focused executable regression was added to the existing adapter-wiring test file.
That exact regression failed against a disposable copy of the target production scripts with expected exit 1 versus actual 153, then passed against the corrected scripts, including a successful retry without the output limit.

The before and after product artifacts show identical original-settings SHA-256 `e6b19ec59657a6005b9b4c12116ab40530b04a7b1a810a4a539233152ba4d478` and mode `0640`.
Before the correction the directory also contained incomplete staging output; afterward only `settings.local.json` remained and the product returned 1 with its existing "left it unchanged" publication refusal.
See `target-partial-before-state.jsonl`, `target-partial-after-state.jsonl`, `target-partial-exact-before.txt`, and `target-partial-regression.txt`.

## Other executable product observations

Initial installation and refresh preserved saved top-level and nested keys, unrelated hook events, custom hooks, and mixed-group metadata.
Same-task replacements retired the old generated incarnation and installed one current generated hook per event.
Switching away from Claude and aborting a replacement left the worker-owned settings and custom hooks.
Malformed settings and a mode-000 unreadable file were refused without changing the original bytes or permissions.
Injected staging, staged-write, and publication failures preserved the original settings and cleaned staging output; retry succeeded.
Secondmate-local settings remained unchanged during synthetic spawn and relaunch checks.
Refreshed hook commands drove the actual semantic busy-state writer, while stale incarnations were rejected.
The corrected secondmate stall fixture passed before and after the additional staged-write correction.
All focused installation, refusal, hook lifecycle, stall, and affected relaunch cases were rechecked after the correction.

The disposable relaunch evidence driver initially inherited the existing test file's plain `rm -rf` cleanup, which could not remove read-only git-hook directories.
Only that disposable driver's cleanup was changed to use the existing shared test cleanup helper; its exact fixture roots were cleaned and all selected relaunch cases were re-driven successfully.
No permanent relaunch-test or unrelated stall assertions were changed.

## Selector behavior

An unknown focused function returned a runner failure.
An exported selected function returning 37 produced a script exit of 37 and a runner failure, rather than false success.
A valid existing selected function succeeded.
See `target-selector-cli.txt` for the actual end-user runner output.

## Live-proof authority limit

The recorded decision requires reading the complete regenerated launch contract before any lifecycle action, and permits only one bounded isolated lab round.
This turn received only a truncated decision record; no complete regenerated launch contract is present in the permitted worktree or named evidence directory.
The runbook itself says generic Test instructions do not replace the generated Herdr lab contract.
The workspace boundary also allows intentional out-of-worktree writes only for evidence, whereas the prescribed named Herdr session persists external user/session state.
No lab preparation, provisioning, worker launch, credential operation, or lifecycle retry was attempted across these unresolved boundaries, so the authorized bounded round has not been consumed.
Provide the complete generated contract through an allowed input and explicitly reconcile the named lab's external state writes with the workspace boundary before requesting the live round.
A missing contract or authority is not evidence that the installed CLI or normal login is unavailable; those are not claimed unavailable here.

No full repository suite, linter, formatter, static analysis, pipeline control, push, PR, or CI phase was executed.
Evidence contains only generic disposable fixtures; code-root and fixture-root paths are normalized in persisted product captures.
Transient drivers and the before-fix source snapshot were removed; only the focused source correction and permanent regression remain in the worktree.
