#!/usr/bin/env bash
set -eu
# Mounts are confined to a fresh private namespace; /bin is never written on host.
mount --make-rprivate /
mount --bind "$PWD/.test-live-bin" /bin
mount --bind "$PWD/.test-live-bin" /usr/bin
export TMPDIR="$PWD/.test-live-tmp"
exec "$@"
