#!/bin/bash
# Build GENIUS Steamworks Builder into a macOS .app bundle (dist/)
set -e
cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
    echo "Setting up .venv (first run)..."
    python3 -m venv .venv
    .venv/bin/pip install --quiet --upgrade pip
    .venv/bin/pip install --quiet -r requirements.txt
fi

echo "============================================"
echo "  Building GENIUS Steamworks Builder.app"
echo "============================================"
.venv/bin/python -m PyInstaller --noconfirm --clean GENIUS.spec
echo
echo "============================================"
echo "  DONE.  ->  dist/GENIUS Steamworks Builder.app"
echo "============================================"
