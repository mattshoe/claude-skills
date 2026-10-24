#!/bin/sh
# Prints the latest version of a skill from GitHub main, so every invocation runs current instructions and scripts.
# Usage: sync.sh PLUGIN SKILL BUNDLED_DIR. Falls back to the last good copy, then the bundled one, when GitHub is unreachable.
set -u
PLUGIN=$1
SKILL=$2
BUNDLED=$3
REPO=mattshoe/claude-skills
CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/claude-skills"
DIR="$CACHE/$SKILL"
SHA=$(git ls-remote "https://github.com/$REPO.git" refs/heads/main 2>/dev/null | cut -f1)
if [ -n "$SHA" ] && [ "$(cat "$DIR/.sha" 2>/dev/null)" != "$SHA" ]; then
  TMP=$(mktemp -d)
  if curl -fsSL --max-time 30 "https://codeload.github.com/$REPO/tar.gz/$SHA" |
    tar -xz -C "$TMP" --strip-components=5 "claude-skills-$SHA/plugins/$PLUGIN/skills/$SKILL" 2>/dev/null &&
    [ -f "$TMP/body.md" ]; then
    mkdir -p "$CACHE"
    rm -rf "$DIR"
    mv "$TMP" "$DIR"
    echo "$SHA" > "$DIR/.sha"
  else
    rm -rf "$TMP"
  fi
fi
if [ ! -f "$DIR/body.md" ]; then
  mkdir -p "$CACHE"
  rm -rf "$DIR"
  cp -R "$BUNDLED" "$DIR"
fi
if [ -n "$SHA" ] && [ "$(cat "$DIR/.sha" 2>/dev/null)" = "$SHA" ]; then
  echo "($SKILL synced to $REPO@$(echo "$SHA" | cut -c1-7))"
else
  echo "(WARNING: could not fetch the latest $SKILL from GitHub, running a cached copy. Tell the user.)"
fi
echo
sed "s#<skill base directory>#$DIR#g" "$DIR/body.md"
echo
echo "---"
echo "To change this skill, edit plugins/$PLUGIN/skills/$SKILL/ in a checkout of github.com/$REPO (body.md and scripts), never the copy in $DIR, which is overwritten on every sync. Commit and push to main right away without being asked, the version bumps on commit."
