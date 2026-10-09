#!/bin/bash
# Set up a Vikash reel-editing project: folder layout, tools, outlet logos, Python venv.
# usage: setup_project.sh <project_dir>
set -euo pipefail
SKILL="$(cd "$(dirname "$0")/.." && pwd)"
P="${1:?usage: setup_project.sh <project_dir>}"
mkdir -p "$P"/{01_footage/raw,01_footage/b-roll,03_graphics,04_project_files,05_exports/shorts,07_scripts_research/scripts,07_scripts_research/news_articles,07_scripts_research/logos,tools}
cp "$SKILL"/scripts/*.py "$P/tools/"
cp -n "$SKILL"/assets/logos/*.png "$P/07_scripts_research/logos/" 2>/dev/null || true
if [ ! -x "$P/.venv/bin/python" ]; then
  python3 -m venv "$P/.venv"
  "$P/.venv/bin/pip" install -q -r "$SKILL/requirements.txt"
fi
command -v ffmpeg >/dev/null || echo "note: no system ffmpeg; reel_kit uses imageio-ffmpeg's binary, but install ffmpeg for ffprobe/silencedetect"
[ -d "/Applications/Google Chrome.app" ] || echo "note: Google Chrome is needed for article/tweet captures"
command -v yt-dlp >/dev/null || echo "note: install yt-dlp (pip install --user yt-dlp) for X video downloads"
echo "project ready: $P"
