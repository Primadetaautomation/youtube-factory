#!/bin/bash
# YouTube Factory — Dubbelklik om te installeren!
# Dit bestand mag je gewoon dubbelklikken vanuit Finder.

clear
echo ""
echo "  ╔═══════════════════════════════════════╗"
echo "  ║     YouTube Factory Installer         ║"
echo "  ║     Even geduld...                    ║"
echo "  ╚═══════════════════════════════════════╝"
echo ""

APP_DIR="$HOME/youtube-factory"

# ── Check & install Homebrew ──────────────────
if ! command -v brew &> /dev/null; then
    echo "  Homebrew installeren (pakketbeheerder voor Mac)..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # Add brew to PATH for Apple Silicon
    if [ -f "/opt/homebrew/bin/brew" ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
fi

# ── Check & install Python ────────────────────
echo "  Python controleren..."
if ! command -v python3 &> /dev/null; then
    echo "  Python installeren..."
    brew install python3
fi
echo "  ✓ $(python3 --version)"

# ── Check & install FFmpeg ────────────────────
echo "  FFmpeg controleren..."
if ! command -v ffmpeg &> /dev/null; then
    echo "  FFmpeg installeren..."
    brew install ffmpeg
fi
echo "  ✓ FFmpeg gevonden"

# ── Check & install Git ───────────────────────
if ! command -v git &> /dev/null; then
    echo "  Git installeren..."
    brew install git
fi

# ── Download app ──────────────────────────────
echo ""
if [ -d "$APP_DIR/.git" ]; then
    echo "  App updaten..."
    cd "$APP_DIR"
    git pull origin main 2>/dev/null || true
else
    echo "  App downloaden..."
    git clone https://github.com/Primadetaautomation/youtube-factory.git "$APP_DIR" 2>/dev/null
fi

cd "$APP_DIR"

# ── Python environment ────────────────────────
echo "  Python omgeving klaarmaken..."
python3 -m venv .venv 2>/dev/null
source .venv/bin/activate

pip install --quiet --upgrade pip 2>/dev/null
pip install --quiet -r requirements.txt 2>/dev/null
pip install --quiet --upgrade yt-dlp 2>/dev/null

echo ""
echo "  ╔═══════════════════════════════════════╗"
echo "  ║     Installatie voltooid! ✓           ║"
echo "  ║     App wordt gestart...              ║"
echo "  ╚═══════════════════════════════════════╝"
echo ""

# ── Start de app ─────────────────────────────
python server.py
