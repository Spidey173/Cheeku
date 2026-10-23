#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

if [ -f "venv/bin/python3" ]; then
    exec venv/bin/python3 run.py "$@"
else
    exec python3 run.py "$@"
fi
