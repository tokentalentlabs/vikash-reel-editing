# Vikash Reel Editing

A Claude Code skill that turns Vikash's raw Hindi/Hinglish talking-head takes into finished 1080x1920 news-commentary reels: retakes removed, research (tweets, whitelisted news articles, ANI clips, photos) placed in an animated top panel, delivered as a Final Cut Pro `.fcpxml` plus a full-res MP4.

## Install
```bash
git clone <this repo> ~/.claude/skills/vikash-reel-editing
```
Then in a project folder ask Claude: "new video, research-heavy, raws are in 01_footage/raw" and paste the script.
First time on a machine: `~/.claude/skills/vikash-reel-editing/scripts/setup_project.sh <project_dir>`.

## Contents
- `SKILL.md` - the workflow and hard rules Claude follows
- `references/` - style guide (layout, whitelist), animation rules, research/capture playbook + review checklist
- `scripts/` - `reel_kit.py` (timeline, animation, FCPXML export, preview render), capture tools (articles, paragraphs, tweets), Whisper transcription, project setup
- `assets/templates/` - two complete `build.py` examples (research-heavy tweet-war reel, video-heavy reel)
- `assets/logos/` - outlet logos for article cards
