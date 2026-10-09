---
name: vikash-reel-editing
description: Edit Vikash's Hindi/Hinglish news-commentary reels (1080x1920, 30 fps, under 2:59) from raw talking-head takes into an animated Final Cut Pro timeline (.fcpxml) plus a full-res MP4. Covers retake removal, Whisper word timing, research (whitelisted news outlets, X/Twitter posts, ANI clips, Wikimedia photos), article/tweet cards with spoken-word highlights, split-screen and circle-PiP layouts with pro-editor animation, fact/defamation flagging, and delivery checks. Use whenever the user drops new raws for a reel, says "new video", "edit this reel", gives a Hinglish script with an edit type (research-heavy, video-heavy, storytelling), or asks to fix/re-render one of these reels.
---

# Vikash Reel Editing

One creator talking to a selfie camera; the top third of the frame carries the proof (tweets, article cards, clips, photos) while he speaks. The output is a Final Cut Pro `.fcpxml` whose every element animates in and out, plus a rendered 1080x1920 30 fps MP4.

Read before planning any edit:
- `references/style-guide.md` - layout, graphic elements, **news-source whitelist**, card rules, circle-PiP.
- `references/animation.md` - every move (push, slide, pop, Ken Burns, PiP) and how `reel_kit` implements it.
- `references/workflow.md` - research playbook (X search, tweet/clip/photo download), card capture tricks, review checklist of past mistakes.

## Project setup (once per machine)

Run `scripts/setup_project.sh <project_dir>`: creates the folder layout, copies the scripts to `<project>/tools/`, the outlet logos to `07_scripts_research/logos/`, and makes `.venv` with `requirements.txt`. Needs ffmpeg (Homebrew or the bundled `imageio-ffmpeg`), Google Chrome (headless captures), and `yt-dlp` for X videos.

```
01_footage/raw/            1.mov, 2.mov, 3.mov  (raws in recording order)
01_footage/b-roll/<ID>/    downloaded clips + photos; panels/ = rendered panel clips
03_graphics/<ID>/          generated PNGs (cards, highlights, bars, tags)
04_project_files/<ID>/     build.py + <ID>_vN.fcpxml
05_exports/shorts/         <ID>_preview.mp4 (half-res, internal) and <ID>_final.mp4 (deliverable)
07_scripts_research/       scripts/<ID>/ transcripts, news_articles/<id>/ captures, logos/
```

## Inputs per video

Raw take(s) in `01_footage/raw/`, the Hinglish script in chat, and the **edit type** (ask if missing):
- **Research-heavy:** tweets, article cards, documents and photos carry the story; at most 2-3 clips.
- **Video-heavy:** real footage of the incident, each clip cross-checked against what the script says; images fill gaps, few articles.
- **Storytelling:** the top panel acts the story out beat by beat (`story_still()` labels/shake/flash/blur/tilt on real photos, at most one built-up infographic).

## Workflow

1. **Transcribe** every raw: `.venv/bin/python tools/transcribe.py 01_footage/raw/N.mov 07_scripts_research/scripts/<ID> large-v3`, then `tools/transcribe_windows.py <out_dir> raws...` for word timings in 8 s windows (long VAD segments drop whole stretches of Hindi). Start both in the background and research meanwhile.
2. **Find retakes and pauses.** Every raw usually opens with false starts ("Elon Musk... Elon Musk bhai sahab", "lekin lekin lekin"). Compare each file's first 10 s with the script, keep only the last clean attempt, and place the cut inside the silence (`ffmpeg -af silencedetect=noise=-32dB:d=0.4`) just before it. End each raw just after its last word (check silencedetect - Whisper word ends run early). Only the **last** raw may have its closing pauses cut.
3. **Research** (playbook in `references/workflow.md`): original tweets of everyone involved, whitelisted articles that prove each factual line, 2-3 clips max for research-heavy (ANI on X is ideal), photos from Wikimedia Commons or outlet tweets. Verify every claim in the script while doing this and note slips.
4. **Beat sheet.** Map each sentence to a panel (or full face for opinion), with file-local times from the word JSON. Flag factual slips and defamation/hate-speech risk lines; flagged lines get **no text graphic** (plain face or a neutral photo + name tag). Share the beat sheet with the flags in the final message.
5. **Build** `04_project_files/<ID>/build.py` from `assets/templates/build_research_heavy.py` (tweets, tweet-war PiP, article cards, pills, photos, clips, multi-segment last raw) or `build_video_heavy.py` (clip-led, bars infographic). `--panels-only` writes just the PNGs for a quick visual check; a plain run writes the `.fcpxml` + half-res preview; `--final` also renders the deliverable.
6. **Check** (see review checklist in `references/workflow.md`), then **deliver the full-res `--final` MP4** (never the preview) and the `.fcpxml` path. The user imports it in Final Cut Pro via File -> Import -> XML...

## Hard rules

- **Length under 2:59.** If over, propose whole sentences to drop (filler/flagged first), get the OK, cut on a panel change.
- **No cuts in the talking head** and no punch-in zooms, except opening retakes of each raw and dead pauses at the very end of the last raw. Raws join back to back in upload order; joins only trim dead air.
- **Frame-accurate:** each take's face clips must share one source-to-timeline offset in the `.fcpxml` (`src_frame()` handles it; connected PiP clips show a different number because their offset is parent-relative), and the preview must have no repeated frames (`mpdecimate` on a 5 s stretch -> 150 frames).
- **Whitelisted news sources only** (style guide). Official/government pages are allowed. If a whitelisted site blocks capture, ask the user for a link instead of substituting another outlet.
- **Article cards fill the panel and look complete:** logo -> headline -> paragraph(s), key sentence highlighted as spoken, page-coloured background, no sliced lines, readable body text (re-shoot narrower if small).
- **Host framing:** split mode keeps the mouth clear (bars on the neck, `BAR_Y_SPLIT`); circle-PiP is a bust shot, not a face close-up.
- **Clean clips:** no other channels' logos, outros, end cards or burned captions (ANI's bug is fine); no blood/violence unless asked up front, blurred even then. Clips play muted under the host unless the user asks for "host freeze + clip with sound".
- Every element animates in and out (`animate_layout`, `bar_motion`, `tag_motion`, `pill_motion`, PiP slide); nothing pops.

## Final message to the user

Lead with the result (length, file, how to import), then: retakes/pauses removed per raw, what's on screen per beat (tweets, articles, clips, photos), the flagged lines and what was done with each, and the sources list.
