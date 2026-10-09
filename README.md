# Vikash Reel Editing

A Claude Code skill that turns raw Hindi/Hinglish talking-head takes into finished 1080x1920 news-commentary reels: retakes removed, research (tweets, whitelisted news articles, ANI clips, photos) placed in an animated top panel, delivered as a Final Cut Pro `.fcpxml` plus a full-res MP4.

## What's inside

| Path | What it is |
|---|---|
| [`SKILL.md`](SKILL.md) | The workflow and hard rules Claude follows (read automatically when the skill triggers) |
| [`references/style-guide.md`](references/style-guide.md) | Layout, graphic elements, **news-source whitelist**, article-card and circle-PiP rules |
| [`references/animation.md`](references/animation.md) | Every animation (push, slide, pop, Ken Burns, PiP) with frame timings |
| [`references/workflow.md`](references/workflow.md) | Research playbook (X search, tweet/clip/photo download), capture commands, build API, review checklist |
| [`scripts/`](scripts) | `reel_kit.py` (timeline, animation, FCPXML export, renders), capture tools, Whisper transcription, `setup_project.sh` |
| [`assets/templates/`](assets/templates) | Two complete `build.py` examples: research-heavy (tweet war) and video-heavy |
| [`assets/logos/`](assets/logos) | Outlet logos for article cards |

## Requirements

- **macOS** (the tools use the Mac paths for Chrome and the Arial fonts)
- **Claude Code** (desktop app recommended: its browser pane is used to search X while signed in)
- **Homebrew**, then `ffmpeg` and `yt-dlp` (the setup script installs both)
- **Google Chrome** (headless screenshots of articles and tweets)
- **Python 3.9+** with **faster-whisper** (Whisper large-v3 for Hindi word timings), Pillow, numpy, requests, websocket-client - all installed into the project's `.venv` by the setup script, which also downloads the ~3 GB Whisper model once
- **Final Cut Pro** to open the timelines (File -> Import -> XML...)
- An X (Twitter) account signed in to in the browser pane, for finding posts and clips

## Install

```bash
# 1. the skill
git clone https://github.com/tokentalentlabs/vikash-reel-editing ~/.claude/skills/vikash-reel-editing

# 2. a project folder (tools, venv, Whisper model, folder layout)
~/.claude/skills/vikash-reel-editing/scripts/setup_project.sh ~/Documents/MyReels
```

Manual Whisper install, if you skip the script:
```bash
python3 -m venv .venv && .venv/bin/pip install faster-whisper
.venv/bin/python -c 'from faster_whisper import WhisperModel; WhisperModel("large-v3", device="cpu", compute_type="int8")'
```

## Use

Open Claude Code in the project folder, drop the raws into `01_footage/raw/` (1.mov, 2.mov, ... in recording order) and say e.g.:
> New video, research-heavy, 3 raws. Remove retakes at the start of each and the silence at the end. Script: ...

## Using it for a different creator

The layout is tuned to Vikash's selfie framing. For another host, check a split-screen frame and adjust in `tools/reel_kit.py`: `FACE_SHIFT` (how far the face moves down in split mode), `BAR_Y_FULL` / `BAR_Y_SPLIT` (text bars on the neck, never over the mouth), and the `face_center` passed to `pip_face_motion()` for the circle-PiP.
