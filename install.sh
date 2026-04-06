#!/bin/bash
# YouTube Factory — Installer
# Installeert alle vereisten en de app zelf op je PC.

set -e

echo ""
echo "  ╔═══════════════════════════════════════╗"
echo "  ║       YouTube Factory Installer       ║"
echo "  ╚═══════════════════════════════════════╝"
echo ""

# ── Check OS ──────────────────────────────────
OS="$(uname -s)"
case "$OS" in
    Darwin) PLATFORM="mac" ;;
    Linux)  PLATFORM="linux" ;;
    MINGW*|MSYS*|CYGWIN*) PLATFORM="windows" ;;
    *) echo "Niet ondersteund OS: $OS"; exit 1 ;;
esac

echo "  Platform: $PLATFORM"
echo ""

# ── Ask permission ────────────────────────────
echo "Dit script installeert:"
echo "  1. Python 3.10+ (als niet aanwezig)"
echo "  2. FFmpeg (voor video bewerking)"
echo "  3. yt-dlp (voor YouTube clip downloads)"
echo "  4. YouTube Factory (Python package)"
echo ""
read -p "Doorgaan met installatie? [j/N] " confirm
if [[ ! "$confirm" =~ ^[jJyY]$ ]]; then
    echo "Installatie geannuleerd."
    exit 0
fi
echo ""

# ── Check Python ──────────────────────────────
echo "→ Python controleren..."
if command -v python3 &> /dev/null; then
    PY=$(python3 --version 2>&1)
    echo "  ✓ $PY gevonden"
else
    echo "  ✗ Python 3 niet gevonden."
    if [ "$PLATFORM" = "mac" ]; then
        echo "  Installeer via: brew install python3"
        read -p "  Wil je dit nu doen? [j/N] " install_py
        if [[ "$install_py" =~ ^[jJyY]$ ]]; then
            if ! command -v brew &> /dev/null; then
                echo "  Homebrew niet gevonden. Installeer eerst: https://brew.sh"
                exit 1
            fi
            brew install python3
        else
            echo "  Installeer Python 3.10+ en draai dit script opnieuw."
            exit 1
        fi
    elif [ "$PLATFORM" = "linux" ]; then
        echo "  Installeer via: sudo apt install python3 python3-pip python3-venv"
        read -p "  Wil je dit nu doen? [j/N] " install_py
        if [[ "$install_py" =~ ^[jJyY]$ ]]; then
            sudo apt update && sudo apt install -y python3 python3-pip python3-venv
        else
            exit 1
        fi
    else
        echo "  Download Python van https://python.org/downloads"
        exit 1
    fi
fi

# ── Check & install Deno (needed by yt-dlp) ───
echo "→ Deno controleren..."
if command -v deno &> /dev/null; then
    echo "  ✓ Deno gevonden"
else
    echo "  Deno installeren (nodig voor YouTube downloads)..."
    if [ "$PLATFORM" = "mac" ]; then
        brew install deno
    elif [ "$PLATFORM" = "linux" ]; then
        curl -fsSL https://deno.land/install.sh | sh
        export PATH="$HOME/.deno/bin:$PATH"
    fi
    echo "  ✓ Deno geinstalleerd"
fi

# ── Check FFmpeg ──────────────────────────────
echo "→ FFmpeg controleren..."
if command -v ffmpeg &> /dev/null; then
    echo "  ✓ FFmpeg gevonden"
else
    echo "  ✗ FFmpeg niet gevonden."
    if [ "$PLATFORM" = "mac" ]; then
        read -p "  Installeren via brew? [j/N] " install_ff
        if [[ "$install_ff" =~ ^[jJyY]$ ]]; then
            brew install ffmpeg
        else
            echo "  Installeer FFmpeg en draai dit script opnieuw."
            exit 1
        fi
    elif [ "$PLATFORM" = "linux" ]; then
        read -p "  Installeren via apt? [j/N] " install_ff
        if [[ "$install_ff" =~ ^[jJyY]$ ]]; then
            sudo apt update && sudo apt install -y ffmpeg
        else
            exit 1
        fi
    else
        echo "  Download FFmpeg van https://ffmpeg.org/download.html"
        exit 1
    fi
fi

# ── Install YouTube Factory ───────────────────
echo "→ YouTube Factory installeren..."

# Create app directory
APP_DIR="$HOME/youtube-factory"
mkdir -p "$APP_DIR"

# Clone or download
if [ -d "$APP_DIR/.git" ]; then
    echo "  Bestaande installatie gevonden, updaten..."
    cd "$APP_DIR"
    git pull origin main 2>/dev/null || true
else
    echo "  Downloaden..."
    if command -v git &> /dev/null; then
        git clone https://github.com/engelbr/youtube-factory.git "$APP_DIR" 2>/dev/null || {
            echo "  Git clone mislukt. Probeer handmatige download..."
            curl -L -o /tmp/yf.tar.gz "https://github.com/engelbr/youtube-factory/archive/refs/heads/main.tar.gz"
            tar -xzf /tmp/yf.tar.gz -C "$APP_DIR" --strip-components=1
            rm /tmp/yf.tar.gz
        }
    else
        curl -L -o /tmp/yf.tar.gz "https://github.com/engelbr/youtube-factory/archive/refs/heads/main.tar.gz"
        tar -xzf /tmp/yf.tar.gz -C "$APP_DIR" --strip-components=1
        rm /tmp/yf.tar.gz
    fi
fi

cd "$APP_DIR"

# Create virtual environment
echo "→ Virtual environment aanmaken..."
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
echo "→ Python packages installeren..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# Install yt-dlp (latest)
echo "→ yt-dlp installeren..."
pip install --quiet --upgrade yt-dlp

echo ""
echo "  ╔═══════════════════════════════════════╗"
echo "  ║      Installatie voltooid! ✓          ║"
echo "  ╚═══════════════════════════════════════╝"
echo ""
echo "  Start YouTube Factory met:"
echo ""
echo "    cd ~/youtube-factory"
echo "    source .venv/bin/activate"
echo "    python server.py"
echo ""
echo "  Of gebruik het snelstart-script:"
echo "    ~/youtube-factory/start.sh"
echo ""
