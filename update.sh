#!/bin/bash
# Updates Tuned in Markets to the latest version. Keeps your .env, data and settings. Stop the app first (Ctrl+C).
cd "$(dirname "$0")"
[ -x .venv/bin/python ] || { echo "Run ./install.sh first."; exit 1; }
.venv/bin/python tools/update.py
