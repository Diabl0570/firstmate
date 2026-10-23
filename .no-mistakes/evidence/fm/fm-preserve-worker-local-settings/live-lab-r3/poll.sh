#!/bin/bash
# poll lab busy record every 0.5s for up to 180s, log changes
S=$1/home/state/$2; last=""; end=$((SECONDS+180))
while [ $SECONDS -lt $end ] && [ -d "$1/home/state" ]; do
  cur="$(cat $S.busy-gen 2>/dev/null) | $(cat $S.busy-state 2>/dev/null)"
  [ "$cur" != "$last" ] && echo "$(date +%T) gen|record: $cur" && last=$cur
  sleep 0.5
done
