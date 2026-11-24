#!/bin/bash
# One-time install on Mac / Linux: a private Python environment in .venv and the libraries. Takes about two minutes.
# Nothing is sent anywhere. The market data and the strategy lab are built by the app itself the first time you run it.
set -e
cd "$(dirname "$0")"
PY=$(command -v python3 || true)
if [ -z "$PY" ]; then echo "Python 3.10 or newer is needed: https://www.python.org/downloads/"; exit 1; fi
"$PY" -c 'import sys; assert sys.version_info >= (3, 10), "Python 3.10 or newer is needed"'
echo "Setting up a private Python environment..."
"$PY" -m venv --clear .venv
.venv/bin/python -m pip install -q --upgrade pip
.venv/bin/python -m pip install -q -r requirements.txt
mkdir -p data
[ -f .env ] || cp .env.example .env
.venv/bin/python tools/setup_contact.py
echo
echo "Installed. Start Tuned in Markets with:  ./run.sh"
echo "The first start builds your data and the strategy lab in the background. Give it 30 to 40 minutes the very first time."
