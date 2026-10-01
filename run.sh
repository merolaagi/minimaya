#!/bin/bash
cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1
exec python3 server.py --host "${MINIMAYA_HOST:-127.0.0.1}" --port "${MINIMAYA_PORT:-48713}"
