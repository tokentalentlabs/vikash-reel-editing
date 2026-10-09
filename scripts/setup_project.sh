#!/bin/bash
# Set up a Vikash reel-editing project on a Mac: checks/installs the tools, makes the folder layout, copies the
# scripts and outlet logos, creates the Python venv (faster-whisper etc.) and downloads the Whisper large-v3 model.
# usage: setup_project.sh <project_dir> [--no-model]
set -euo pipefail
SKILL="$(cd "$(dirname "$0")/.." && pwd)"
P="${1:?usage: setup_project.sh <project_dir> [--no-model]}"
[ "$(uname)" = "Darwin" ] || echo "warning: built for macOS (Chrome path, Arial fonts); other systems need path edits in tools/"

# --- system tools (Homebrew) ---
BREW="$(command -v brew || ls /opt/homebrew/bin/brew /usr/local/bin/brew 2>/dev/null | head -1 || true)"
for tool in ffmpeg yt-dlp; do
  if ! command -v "$tool" >/dev/null; then
    if [ -n "$BREW" ]; then echo "installing $tool..."; "$BREW" install "$tool"
    else echo "MISSING: $tool - install Homebrew (https://brew.sh) then: brew install $tool"; fi
  fi
done
[ -d "/Applications/Google Chrome.app" ] || echo "MISSING: Google Chrome (needed for article/tweet screenshots) - https://www.google.com/chrome/"
[ -f "/System/Library/Fonts/Supplemental/Arial Black.ttf" ] || echo "MISSING: Arial Black font (macOS ships it in /System/Library/Fonts/Supplemental)"
python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))' || { echo "Python 3.9+ required (brew install python)"; exit 1; }

# --- project layout ---
mkdir -p "$P"/{01_footage/raw,01_footage/b-roll,03_graphics,04_project_files,05_exports/shorts,07_scripts_research/scripts,07_scripts_research/news_articles,07_scripts_research/logos,tools}
cp "$SKILL"/scripts/*.py "$P/tools/"
cp -n "$SKILL"/assets/logos/*.png "$P/07_scripts_research/logos/" 2>/dev/null || true

# --- Python venv: faster-whisper (transcription), Pillow/numpy (graphics), requests/websocket-client (captures) ---
if [ ! -x "$P/.venv/bin/python" ]; then python3 -m venv "$P/.venv"; fi
"$P/.venv/bin/pip" install -q --upgrade pip
"$P/.venv/bin/pip" install -q -r "$SKILL/requirements.txt"

# --- Whisper model (~3 GB, cached in ~/.cache/huggingface; downloaded once per machine) ---
if [ "${2:-}" != "--no-model" ]; then
  echo "downloading Whisper large-v3 (~3 GB, first time only)..."
  "$P/.venv/bin/python" -c 'from faster_whisper import WhisperModel; WhisperModel("large-v3", device="cpu", compute_type="int8"); print("whisper large-v3 ready")'
fi
echo "project ready: $P  (put raws in $P/01_footage/raw as 1.mov, 2.mov, ...)"
