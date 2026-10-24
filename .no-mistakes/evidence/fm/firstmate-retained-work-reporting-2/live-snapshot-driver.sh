#!/usr/bin/env bash
set -euo pipefail
ROOT=$PWD
EVIDENCE=/home/kasper/.no-mistakes/evidence/01M5P91F5H9J68964T99S351S3
# Keep the Unix socket name below Linux's sockaddr_un limit without external writes.
LAB=$(mktemp -d "$ROOT/l.XXXXXX")
cleanup() {
  TMUX_TMPDIR="$LAB/tmux" tmux -L fm-lab kill-server 2>/dev/null || true
  rm -rf "$LAB"
}
trap cleanup EXIT
bin/fm-lab-home.sh create "$LAB"
mkdir -p "$LAB/tmux"
touch "$LAB/config/supervision-host"
env -u NO_MISTAKES_GATE -u FM_GATE_REFUSE_BYPASS -u FM_ROOT_OVERRIDE -u FM_STATE_OVERRIDE -u FM_DATA_OVERRIDE -u FM_CONFIG_OVERRIDE -u FM_PROJECTS_OVERRIDE DISABLE_AUTOUPDATER=1 TMUX_TMPDIR="$LAB/tmux" tmux -L fm-lab new-session -d -s primary -n fm-review -x 120 -y 40 -c "$PWD" -e FM_HOME="$LAB" claude
TMUX_TMPDIR="$LAB/tmux" tmux -L fm-lab set-window-option -t primary:fm-review automatic-rename off
SOCKET="$LAB/tmux/tmux-$(id -u)/fm-lab"
export TMUX="$SOCKET,0,0"
export TMUX_TMPDIR="$LAB/tmux" FM_HOME="$LAB" TMPDIR="$ROOT/.validation-tmp"
unset FM_ROOT_OVERRIDE FM_STATE_OVERRIDE FM_DATA_OVERRIDE FM_CONFIG_OVERRIDE FM_PROJECTS_OVERRIDE
for i in $(seq 1 40); do
  tmux -L fm-lab capture-pane -p -t primary > "$EVIDENCE/claude-lab-pane.txt"
  if grep -Eq 'trust|Welcome|Claude Code|log in|Login|theme|safety check' "$EVIDENCE/claude-lab-pane.txt"; then break; fi
  sleep 0.25
done
printf '\n--- actual lab harness pane ---\n'
tmux -L fm-lab capture-pane -p -t primary
printf '\n--- real endpoint recovery verdict ---\n'
bash -c '. "$1/bin/fm-backend.sh"; fm_backend_agent_alive tmux primary:fm-review; echo' _ "$ROOT"
mkdir -p "$LAB/projects/review" "$LAB/data/review"
cat > "$LAB/state/review.meta" <<EOF
backend=tmux
window=primary:fm-review
worktree=$LAB/projects/review
project=sample
harness=claude
kind=scout
mode=scout
EOF
cat > "$LAB/data/backlog.md" <<'EOF'
## In flight
- [ ] review - Completed evidence retained for approval (repo: sample) (kind: scout) (hold: retain report) (hold-kind: captain)

## Queued

## Done
EOF
printf '# Disposable review evidence\n' > "$LAB/data/review/report.md"
printf 'done: report delivered\n' > "$LAB/state/review.status"
GEN=$(bin/fm-busy-event.sh arm "$LAB/state" review)
bin/fm-busy-event.sh apply "$LAB/state" review idle --gen "$GEN" --source claude-hook --event stop
bin/fm-fleet-snapshot.sh --secondmate-home-summary > "$EVIDENCE/live-retained-scout.json"
jq -e '.valid and .state == "captain_decision" and .counts.retained_attempts == 1 and .counts.active_children == 0 and .counts.landed == 0 and (.retained_attempts[0] | .id == "review" and .state == "done" and .runtime_activity.state == "idle") and any(.decisions_open[]; .id == "review" and .verb == "captain-hold") and any(.holds[]; .id == "review")' "$EVIDENCE/live-retained-scout.json"
printf '\n--- retained scout with captain hold (actual CLI output) ---\n'
jq '{valid,state,retained_attempts,active_children,decisions_open,holds,landed,counts}' "$EVIDENCE/live-retained-scout.json"
# A terminal declaration without a structured hold is still contradictory.
cp "$LAB/data/backlog.md" "$LAB/backlog-held"
printf '## In flight\n- [ ] review - Review (repo: sample) (kind: scout)\n\n## Queued\n\n## Done\n' > "$LAB/data/backlog.md"
bin/fm-fleet-snapshot.sh --secondmate-home-summary > "$EVIDENCE/live-unheld-terminal.json"
jq -e '.valid == false and .invalidity == {kind:"terminal_in_flight",ids:["review"]} and .counts.retained_attempts == 0' "$EVIDENCE/live-unheld-terminal.json"
printf '\n--- terminal evidence without a hold remains contradictory ---\n'
jq '{valid,state,invalidity,retained_attempts}' "$EVIDENCE/live-unheld-terminal.json"
cp "$LAB/backlog-held" "$LAB/data/backlog.md"
# A new semantic busy event wins over the historical delivered-report wording.
bin/fm-busy-event.sh apply "$LAB/state" review busy --gen "$GEN" --source claude-hook --event user-prompt-submit
bin/fm-fleet-snapshot.sh --secondmate-home-summary > "$EVIDENCE/live-busy-continuation.json"
jq -e '.valid and .counts.retained_attempts == 0 and any(.active_children[]; .id == "review" and .state == "working") and any(.decisions_open[]; .verb == "captain-hold") and .counts.landed == 0' "$EVIDENCE/live-busy-continuation.json"
printf '\n--- semantic busy event remains current work despite an existing report ---\n'
jq '{valid,state,active_children,retained_attempts,decisions_open,landed}' "$EVIDENCE/live-busy-continuation.json"
# Removing semantic evidence must not turn a delivered report into current truth.
rm "$LAB/state/review.busy-state"
printf 'needs-decision [key=follow-up]: select the follow-up\n' >> "$LAB/state/review.status"
bin/fm-fleet-snapshot.sh --secondmate-home-summary > "$EVIDENCE/live-unknown-scout.json"
jq -e '.valid == false and .state == "unknown" and .invalidity == {kind:"child_current_unavailable",ids:["review"]} and .counts.retained_attempts == 0 and any(.decisions_open[]; .key == "follow-up") and any(.decisions_open[]; .verb == "captain-hold")' "$EVIDENCE/live-unknown-scout.json"
printf '\n--- missing semantic evidence keeps the call open ---\n'
jq '{valid,state,invalidity,retained_attempts,decisions_open,holds,landed}' "$EVIDENCE/live-unknown-scout.json"
# Restore the state but give the record an untrusted generation.
bin/fm-busy-event.sh apply "$LAB/state" review idle --gen "$GEN" --source claude-hook --event stop
printf 'different-generation\n' > "$LAB/state/review.busy-gen"
bin/fm-fleet-snapshot.sh --json > "$EVIDENCE/live-stale-generation.json"
jq -e '.tasks[0] | .current_state.state == "unknown" and .runtime_activity.state == "unknown" and .hints.pending_decision' "$EVIDENCE/live-stale-generation.json"
printf '\n--- stale generation is not idle or completed ---\n'
jq '.tasks[0] | {id,current_state,runtime_activity,hints}' "$EVIDENCE/live-stale-generation.json"
# A busy record must not survive a hung read or positive endpoint death as execution evidence.
GEN=$(bin/fm-busy-event.sh arm "$LAB/state" review)
bin/fm-busy-event.sh apply "$LAB/state" review busy --gen "$GEN" --source claude-hook --event user-prompt-submit
printf '\n--- suspend owned lab server; bound real endpoint clients across all mechanisms ---\n'
python3 .validation-tmp/live-bounded-endpoint.py
tmux -L fm-lab kill-session -t primary
bin/fm-fleet-snapshot.sh --json > "$EVIDENCE/live-endpoint-gone.json"
jq -e '.tasks[0] | .runtime_activity.state == "dead" and .runtime_activity.source == "endpoint-gone" and .hints.pending_decision' "$EVIDENCE/live-endpoint-gone.json"
printf '\n--- a stale busy record behind a missing endpoint is dead, not active ---\n'
jq '.tasks[0] | {id,current_state,runtime_activity,endpoint,hints}' "$EVIDENCE/live-endpoint-gone.json"
