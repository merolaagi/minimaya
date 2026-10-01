#!/bin/bash
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${MINIMAYA_DEST:-$HOME/Sites/minimaya}"
PORT="${MINIMAYA_PORT:-48713}"
HOST="${MINIMAYA_HOST:-127.0.0.1}"
LABEL="com.manish.minimaya"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
VERSION="$(cat "$SRC/VERSION")"
BUILD="$(cat "$SRC/BUILD")"

say(){ printf '\033[1;33m>\033[0m %s\n' "$*"; }
ok(){ printf '\033[1;32m✓\033[0m %s\n' "$*"; }
fail(){ printf '\033[1;31mx %s\033[0m\n' "$*" >&2; exit 1; }

PY="$(command -v python3 || true)"
[ -n "$PY" ] || fail "python3 not found. Run: xcode-select --install   (or: brew install python)"
"$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' || fail "Python 3.8 or newer is required"
PY="$("$PY" -c 'import sys; print(sys.executable)')"
ok "Python: $PY"

FF="$(command -v ffmpeg || true)"
for c in /opt/homebrew/bin/ffmpeg /usr/local/bin/ffmpeg; do [ -z "$FF" ] && [ -x "$c" ] && FF="$c"; done
if [ -z "$FF" ] && [ "${MINIMAYA_NO_FFMPEG:-0}" != "1" ]; then
  BREW="$(command -v brew || true)"
  for c in /opt/homebrew/bin/brew /usr/local/bin/brew; do [ -z "$BREW" ] && [ -x "$c" ] && BREW="$c"; done
  if [ -n "$BREW" ]; then
    say "Installing ffmpeg with Homebrew for MP4 movie export (one time, a few minutes; MINIMAYA_NO_FFMPEG=1 skips)"
    "$BREW" install ffmpeg >/dev/null && FF="$(dirname "$BREW")/ffmpeg" || say "Homebrew could not install ffmpeg; MP4 export stays off, WebM playblasts still work"
  else
    say "No Homebrew found, so no ffmpeg: MP4 movie export stays off (install Homebrew, then brew install ffmpeg)"
  fi
fi
[ -n "$FF" ] && ok "ffmpeg: $FF (MP4 movies with sound)"

say "Installing Mini Maya Studio $VERSION (build $BUILD) into $DEST"
mkdir -p "$DEST/data/scenes" "$DEST/data/assets" "$DEST/data/renders" "$DEST/logs" "$DEST/releases"
if [ -f "$DEST/VERSION" ] && [ -f "$DEST/index.html" ]; then
  OLD="$(cat "$DEST/VERSION")-$(cat "$DEST/BUILD" 2>/dev/null || echo old)"
  tar -czf "$DEST/releases/backup-$OLD.tgz" -C "$DEST" --exclude ./data --exclude ./logs --exclude ./releases --exclude ./.git . 2>/dev/null || true
  ls -1t "$DEST"/releases/backup-*.tgz 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true
  ok "Backed up previous build $OLD to releases/"
fi
if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete --exclude=/data --exclude=/logs --exclude=/releases --exclude=/.git "$SRC/" "$DEST/"
else
  (cd "$SRC" && tar -cf - .) | (cd "$DEST" && tar -xf -)
fi
chmod +x "$DEST"/*.sh "$DEST/server.py"
ok "Files copied (your saved scenes in data/ were left untouched)"

if [ "$(uname)" = "Darwin" ]; then
  launchctl bootout "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
  sleep 1
  PIDS="$(lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null || true)"
  if [ -n "$PIDS" ]; then
    ps -o pid=,command= -p $PIDS >&2 || true
    fail "Port $PORT is already in use by the process above. Re-run with MINIMAYA_PORT=<other 5-digit port>."
  fi
  mkdir -p "$HOME/Library/LaunchAgents"
  cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PY</string>
    <string>$DEST/server.py</string>
    <string>--host</string><string>$HOST</string>
    <string>--port</string><string>$PORT</string>
  </array>
  <key>WorkingDirectory</key><string>$DEST</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$DEST/logs/server.log</string>
  <key>StandardErrorPath</key><string>$DEST/logs/server.log</string>
</dict>
</plist>
PL
  for i in 1 2 3 4 5; do
    launchctl bootstrap "gui/$(id -u)" "$PLIST" 2>/dev/null && break
    sleep 1
    [ "$i" = 5 ] && fail "launchctl could not load $PLIST"
  done
  ok "Background service $LABEL loaded (starts at login, restarts if it stops)"
else
  say "Not macOS: starting in the background with nohup"
  pkill -f "[s]erver.py --host $HOST --port $PORT" 2>/dev/null || true
  nohup "$PY" "$DEST/server.py" --host "$HOST" --port "$PORT" >> "$DEST/logs/server.log" 2>&1 &
fi

URL="http://localhost:$PORT"
for i in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1; then break; fi
  sleep 0.3
  [ "$i" = 30 ] && { tail -n 20 "$DEST/logs/server.log" >&2 || true; fail "Server did not answer on port $PORT"; }
done
ok "Server is up: $URL"

if command -v git >/dev/null 2>&1; then
  cd "$DEST"
  [ -d .git ] || git init -q -b main
  git add -A
  if git commit -qm "Mini Maya Studio $VERSION (build $BUILD)" >/dev/null 2>&1; then
    git tag -f "build-$BUILD" >/dev/null 2>&1 || true
    ok "Committed build $BUILD to the local git repo"
  else
    say "Nothing new to commit (or git user.name/user.email not set)"
  fi
  if [ "${MINIMAYA_NO_PUSH:-0}" != "1" ] && command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    if ! git remote get-url origin >/dev/null 2>&1; then
      if gh repo view minimaya >/dev/null 2>&1; then
        git remote add origin "$(gh repo view minimaya --json url -q .url).git"
      else
        gh repo create minimaya --public --source . --remote origin --description "Mini Maya Studio: a small Maya-style 3D animation studio in the browser" >/dev/null && ok "Created public GitHub repo minimaya"
      fi
    fi
    if git push -q -u origin main --tags 2>/dev/null; then ok "Pushed to $(git remote get-url origin)"; else say "GitHub push failed; run 'git push -u origin main --tags' in $DEST to see why"; fi
  else
    say "Skipped GitHub push (needs the gh CLI logged in; set MINIMAYA_NO_PUSH=1 to silence)"
  fi
fi

echo
ok "Mini Maya Studio $VERSION is running at $URL"
echo "   App folder:  $DEST"
echo "   Scenes:      $DEST/data/scenes"
echo "   Movies:      $DEST/data/renders"
echo "   Logs:        $DEST/logs/server.log"
echo "   Control:     $DEST/ctl.sh status|restart|stop|start|logs"
[ "$(uname)" = "Darwin" ] && [ "${MINIMAYA_NO_OPEN:-0}" != "1" ] && open "$URL" || true
