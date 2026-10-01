#!/bin/bash
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LABEL="com.manish.minimaya"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
PORT="$(/usr/libexec/PlistBuddy -c 'Print :ProgramArguments:5' "$PLIST" 2>/dev/null || echo "${MINIMAYA_PORT:-48713}")"
case "${1:-status}" in
  start)   launchctl bootstrap "gui/$(id -u)" "$PLIST" && echo "started on port $PORT" ;;
  stop)    launchctl bootout "gui/$(id -u)/$LABEL" && echo "stopped" ;;
  restart) launchctl kickstart -k "gui/$(id -u)/$LABEL" && echo "restarted on port $PORT" ;;
  logs)    tail -n 50 -f "$DIR/logs/server.log" ;;
  open)    open "http://localhost:$PORT" ;;
  status)
    if curl -fsS "http://127.0.0.1:$PORT/api/health"; then echo; echo "running: http://localhost:$PORT"; else echo "not answering on port $PORT"; exit 1; fi ;;
  *) echo "usage: ctl.sh start|stop|restart|status|logs|open"; exit 2 ;;
esac
