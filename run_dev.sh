#!/bin/bash
# Run GENIUS Steamworks Builder without building (dev mode, macOS/Linux).
# Creates a local .venv with the dependencies on first run.
set -e
cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
    echo "Setting up .venv (first run)..."
    python3 -m venv .venv
    .venv/bin/pip install --quiet --upgrade pip
    .venv/bin/pip install --quiet -r requirements.txt
fi

exec .venv/bin/python genius_builder.py
