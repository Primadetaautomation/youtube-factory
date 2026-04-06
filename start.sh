#!/bin/bash
# YouTube Factory — Start script
cd "$(dirname "$0")"
source .venv/bin/activate 2>/dev/null || { echo "Draai eerst install.sh"; exit 1; }
python server.py
