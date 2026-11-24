#!/bin/bash
# Starts Tuned in Markets so YOUR devices can open it from anywhere over Tailscale (a free private network between your own devices).
# No public link, no bandwidth cap, nothing exposed to the internet or to the Wi-Fi around you: only devices signed in to your
# Tailscale account can reach it. The Mac must stay on and awake (this script keeps it awake while it runs).
cd "$(dirname "$0")"
TS=$(command -v tailscale || true)
[ -z "$TS" ] && [ -x /Applications/Tailscale.app/Contents/MacOS/Tailscale ] && TS=/Applications/Tailscale.app/Contents/MacOS/Tailscale
if [ -z "$TS" ]; then
  echo "Tailscale is not installed on this Mac. Install it from https://tailscale.com/download, sign in, then run this again."
  exit 1
fi
IP=$("$TS" ip -4 2>/dev/null | head -1)
if [ -z "$IP" ]; then
  echo "Tailscale is installed but this Mac is not connected. Open the Tailscale app, sign in, switch it on, then run this again."
  exit 1
fi
[ -x .venv/bin/python ] || { echo "Run ./install.sh first."; exit 1; }
if curl -s -m 2 -o /dev/null "http://$IP:8810/api/status"; then echo "Already running: http://$IP:8810"; exit 0; fi
echo
echo "Tuned in Markets is starting. Open it on any device signed in to your Tailscale account:"
echo
echo "    http://$IP:8810"
echo
echo "Keep this window open. Control+C stops it."
echo
# once it is up: open it on this Mac too, and say plainly whether it answers
( sleep 7
  if curl -s -m 5 -o /dev/null "http://$IP:8810/api/status"; then
    echo ">>> It is up. Opening http://$IP:8810 on this Mac. On your other devices type the same address, starting with http://"
    opener=$(command -v open || command -v xdg-open || true); [ -n "$opener" ] && "$opener" "http://$IP:8810" >/dev/null 2>&1
  else
    echo ">>> It did not answer at http://$IP:8810 yet. Give it a few more seconds, then try that address in a browser on this Mac."
  fi ) &
TUNED_HOST="$IP" exec caffeinate -is .venv/bin/python -u app.py
