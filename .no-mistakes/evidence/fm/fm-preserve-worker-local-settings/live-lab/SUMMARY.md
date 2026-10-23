# PR #7074 live Claude spawn/relaunch evidence (head 9c134651d00c0d6d64e4d5fb6fbcba9399f261e8)
Claude Code 2.1.309, tmux 3.7c, the existing CLAUDE_CONFIG_DIR login (not changed). Lab: bin/fm-live-lab.sh up --harness claude --worker --effort low --supervision-host off --expect-host no (private tmux). All readiness checks passed (up.log).
No "Allow external CLAUDE.md file imports?" or any other consent prompt appeared (worker-pane-incarnation*.txt).
1. Real fm-spawn worker: gen g1792771538.67119.28057. Claude's own hooks fired user-prompt-submit (busy, seq2), then stop (idle, seq3).
2. Seeded the worker's .claude/settings.local.json with permissions.allow Read(./README.md), the sentinel fmLabSentinel.nested.keep, and the worker's own PostToolUse hook (settings-02).
3. Relaunched with the real fm-control.sh relaunch --note (relaunch.log, exit 0). The old run emitted session-end (seq4). The new gen g1792771596.77757.20162 was armed with launch-brief, then Claude's hooks fired user-prompt-submit (busy) and stop (idle) (busy-transitions.log).
4. settings-03-after-relaunch.json still holds the permission rule, the sentinel and the worker's own hook. The firstmate hooks now carry only the new gen; the old gen is gone.
Cleanup: the down helper exited 0. The lab root, tmux dir, task temp dirs and processes are gone, and 0 lab trust entries remain. The Claude store's project keys match the pre-run snapshot. The store's top-level key set changed; no top-level key path names the lab (the vendor rewrites this store; not attributed to the lab).
