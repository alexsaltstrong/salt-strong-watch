#!/bin/bash
# Optional Mac preview runner. Fetches public Salt Strong articles read-only.
set -u
cd "$(dirname "$0")" || exit 1
printf '\nSALT STRONG WATCH - REAL LONG-FORM VIDEO TEST\n'
printf 'This downloads publicly available article pages only. No WordPress changes.\n\n'
if ! command -v python3 >/dev/null 2>&1; then
  echo 'Python 3 is required. Open the README for instructions.'
  read -r -p 'Press Return to close...' _;exit 1
fi
if [ ! -d '.venv' ];then python3 -m venv .venv || exit 1;fi
source .venv/bin/activate
python -m pip -q install requests beautifulsoup4 playwright || exit 1
# Full page rendering is optional but is recommended for rendered shortcodes.
python -m playwright install chromium || echo 'Could not install Chromium. Continuing with HTML-only extraction.'
echo 'Inspecting six real public long-form articles...'
python sync_catalog.py --mode urls --urls-file longform-test-urls.txt --limit 6 --render-js --delay 0.8 --output catalog.json --report import-audit.json
status=$?
echo 'Import complete. The audit file lists individual successes and failures.'
if [ "$status" -ne 0 ];then echo 'The importer could not reach the site. Preview will show demo content until a real catalog exists.';fi
PORT=8765
echo "Starting preview at http://localhost:$PORT/"
python -m http.server "$PORT" &
server_pid=$!
trap 'kill "$server_pid" 2>/dev/null || true' EXIT
sleep 1
open "http://localhost:$PORT/" >/dev/null 2>&1 || true
wait "$server_pid"
