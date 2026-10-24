#!/bin/sh
# Copies sync.sh into every skill. Run after editing sync.sh, then commit.
cd "$(dirname "$0")"
for d in plugins/*/skills/*/; do cp sync.sh "$d/sync.sh"; done
