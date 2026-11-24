#!/bin/bash
# Installs TradingAgents by Tauric Research (Apache-2.0) into ~/tradingagents with its own private Python environment, so the
# "Deep research" button in Tuned in Markets can run it. About 3 to 5 minutes. Nothing is sent anywhere.
set -e
DEST="$HOME/tradingagents"
PY=$(command -v python3 || true)
[ -z "$PY" ] && { echo "Python 3.10+ is needed: https://www.python.org/downloads/"; exit 1; }
# pinned to the release this app was tested with, straight from the authors' own repository
if [ ! -d "$DEST/.git" ]; then
  git clone --depth 1 --branch v0.3.1 https://github.com/TauricResearch/TradingAgents "$DEST"
else
  git -C "$DEST" fetch --depth 1 origin tag v0.3.1 && git -C "$DEST" checkout -q v0.3.1
fi
cd "$DEST"
"$PY" -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q .
echo
echo "Installed in $DEST"
echo "Next: put your LLM key in tuned-in-markets/.env (see .env.example), then restart Tuned in Markets."
