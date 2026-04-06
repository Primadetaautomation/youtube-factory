#!/bin/bash
# YouTube Factory — Dubbelklik om te starten!
cd "$HOME/youtube-factory"
source .venv/bin/activate 2>/dev/null || {
    echo "YouTube Factory is nog niet geinstalleerd."
    echo "Dubbelklik eerst op 'YouTube Factory Installer.command'"
    read -p "Druk op Enter om te sluiten..."
    exit 1
}
echo ""
echo "  YouTube Factory wordt gestart..."
echo "  Browser opent zo op http://localhost:3333"
echo ""
python server.py
