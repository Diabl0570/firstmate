#!/usr/bin/env bash
# Drives real bin/fm-spawn.sh (stubbed transports) as a Claude crewmate against
# a worktree with saved settings; prints settings.local.json before/after.
ROOT=$1
cd "$ROOT"
. tests/fixtures.sh
ROOT=$1
TMP_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/fm-transcript.XXXXXX"); trap 'chmod -R u+w "$TMP_ROOT"; rm -rf "$TMP_ROOT"' EXIT
eval "$(sed -n '/^make_spawn_case()/,/^}/p;/^run_spawn()/,/^}/p;/^read_case_record()/,/^}/p' tests/fm-busy-adapter-wiring.test.sh)"
id=demo-preserve
read_case_record "$(make_spawn_case demo claude $id)"
S=$WT_DIR/.claude/settings.local.json; mkdir -p "${S%/*}"
printf '.claude/settings.local.json\n' >> "$PROJ_DIR/.git/info/exclude"
cat > "$S" <<'J'
{"permissions":{"allow":["Bash(npm test:*)","Read(./docs/**)"]},
 "hooks":{"PreToolUse":[{"matcher":"Bash","hooks":[{"type":"command","command":"./my-guard.sh"}]}]}}
J
chmod 640 "$S"
echo "=== BEFORE spawn (worker-saved settings, mode $(stat -f %Lp "$S")) ==="; jq . "$S"
echo "=== fm-spawn.sh claude crewmate (1st) ==="; run_spawn "$HOME_DIR" "$WT_DIR" "$FAKEBIN_DIR" "$id" "$PROJ_DIR" >/dev/null; echo "exit=$?"
echo "=== AFTER 1st spawn (mode $(stat -f %Lp "$S")) ==="; jq '{permissions, hook_events: (.hooks|keys), PreToolUse: .hooks.PreToolUse, generated_cmd_count: ([.hooks[][].hooks[].command|select(contains("fm-busy-event.sh"))]|length)}' "$S"
echo "=== ADVERSARIAL: malformed settings (fresh task) ==="
id=demo-malformed; read_case_record "$(make_spawn_case bad claude $id)"
S=$WT_DIR/.claude/settings.local.json; mkdir -p "${S%/*}"; printf '.claude/settings.local.json\n' >> "$PROJ_DIR/.git/info/exclude"
printf '{"permissions":{"allow":["Bash(ls)"]},' > "$S"; cp "$S" "$TMP_ROOT/bad-copy.json"
out=$(run_spawn "$HOME_DIR" "$WT_DIR" "$FAKEBIN_DIR" "$id" "$PROJ_DIR"); echo "exit=$?"; printf '%s\n' "$out" | grep -i -E 'error|claude worker'
cmp -s "$S" "$TMP_ROOT/bad-copy.json" && echo "malformed file left byte-identical: yes" || echo "malformed file CHANGED"
