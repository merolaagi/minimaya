#!/bin/bash
LABEL="com.manish.minimaya"
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null && echo "Stopped $LABEL"
rm -f "$HOME/Library/LaunchAgents/$LABEL.plist" && echo "Removed launch agent"
echo "App files and saved scenes are still in $(cd "$(dirname "$0")" && pwd). Delete that folder yourself if you want them gone."
