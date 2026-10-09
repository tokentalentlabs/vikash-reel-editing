# Workflow reference: research, captures, build API, review checklist

## 1. Research playbook

### X / Twitter (best source for "tweet war" videos)
- Search in the browser pane while the user is signed in to X: `https://x.com/search?q=<query>&f=top`. Useful operators: `from:ANI`, `(from:ndtv OR from:IndianExpress OR from:the_hindu OR from:IndiaToday OR from:ThePrintIndia)`, `since:2026-10-07 until:...`, `filter:videos`, `filter:images`.
- Collect post links + text with JS in the page (scroll a few times):
  ```js
  const seen = new Map();
  for (let i = 0; i < 4; i++) { await new Promise(r => setTimeout(r, 2500));
    document.querySelectorAll('article').forEach(a => {
      const l = [...a.querySelectorAll('a[href*="/status/"]')].map(x => x.getAttribute('href')).find(h => /status\/\d+$/.test(h));
      if (l && !seen.has(l)) seen.set(l, (a.querySelector('video') ? '[VID] ' : '') + a.innerText.replace(/\n/g, ' ').slice(0, 200)); });
    window.scrollBy(0, 2500); }
  [...seen].map(([k, v]) => k + ' | ' + v).join('\n')
  ```
- Without a login: news articles embed the tweets. `curl` the article and grep `(twitter|x)\.com/\w+/status/\d+`.
- Tweet JSON (text, quoted tweet, reply-to, media, link URLs) without login: `https://cdn.syndication.twimg.com/tweet-result?id=<ID>&token=a`. Video files: `mediaDetails[].video_info.variants` (take the highest-bitrate mp4); photos: `media_url_https + '?name=large'`. `yt-dlp https://x.com/<user>/status/<id>` also works.
- News outlets' posts link to the article (`entities.urls[].expanded_url`), which gives whitelisted article URLs fast.

### Clips
- Research-heavy: 2-3 clips max. ANI `#WATCH` posts (ministers, party spokespeople reacting) are ideal and their ANI bug is allowed.
- Check frames across the whole used range (incl. the 0.45 s tail) for other logos, outros, burned captions.
- Crop to the speaker when the backdrop is busy: `clip(..., crop="w:h:x:y")`.

### Photos
- Wikimedia Commons API (send a User-Agent with contact info; it rate-limits with 429, so wait 20-30 s and retry):
  `https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch=<q> filetype:bitmap&gsrnamespace=6&prop=imageinfo&iiprop=url|size&iiurlwidth=1600&format=json`
- Outlet tweets' photos are good for people Commons lacks at good resolution (check corners for logos).

### Fact-checking while researching
Check every date, number and "X did Y" in the script against a whitelisted source. Typical slips: wrong month, attributing a government policy to a person, a place with no report behind it. Note each one for the beat sheet.

## 2. Captures

| What | Command | Notes |
|---|---|---|
| Article (desktop) | `SHOT_W=900 SHOT_DPR=2.4 SHOT_MOBILE=0 tools/article_shot.py URL stem "phrase" ...` | Writes `stem.png` + `stem.json` (h1 lines, blocks, phrase rects, logo box). Pass every phrase you will highlight, copied exactly from the block text (curly quotes matter). |
| Small body text on the card | `SHOT_W=600 ...`, or default mobile layout (no env vars) | The Hindu's desktop body is tiny; mobile reads well. |
| Pages that only paint on-screen text (Deccan Herald) | `PARA_W=600 tools/para_shot.py URL stem "needle in paragraph" "highlight phrase"` | Scrolls first so lazy paragraphs mount. If it fails, shorten the needle; DH often only exposes the subheading/pull-quote. Use `para_card()` in build.py. |
| Late slide-in ads | add `SHOT_H=3200` | |
| Tweet | `tools/tweet_shot.py ID stem "phrase" "last phrase of the tweet text"` | Pass the tweet's last phrase so `tweet_cut()` can drop the quoted post/media/footer. Retry if it errors with "0 height" (embed slow). |
| Outlet logo | crop it from the capture's header into `07_scripts_research/logos/<outlet>.png` | Crop the whole masthead incl. wordmark; never start a crop box at x<0 (renders a black line). |

## 3. build.py API (tools/reel_kit.py + template helpers)

- `TAKES = [(segment, src_in, src_out), ...]` with `RAWFILE = {segment: raw index}`; a last raw with an internal end-pause cut becomes two segments pointing at the same raw. `T(seg, sec)` maps file-local seconds to the timeline.
- `FULL = {seg: [(a, b), ...]}` full-face windows; `PIP = {seg: (a, b)}` circle-PiP window; everything else is split screen.
- Panels (track `P` + highlights `H0..H2`, one group each, pushed left into each other by `animate_layout`):
  - `still_panel(img, seg, a, b, name, spread(rects, w0, w1))` - card/tweet with highlight wipes timed to the words.
  - `tweet(stem, last_phrase)` -> `(panel, phrase_rects)`; `article(stem, ["h1", block_or_phrase...], logo)` -> `(card, rects_fn, meta)`; `para_card(stem, phrase, logo)`.
  - `photo(img, seg, a, b, name, focus)` - blur-fill + Ken Burns; `clip(src, t0, seg, a, b, name, focus, crop)` - muted footage.
  - `pills(title, rows, times, seg, a, b, name)` - red pills sliding in per spoken item (checklists, lists of places).
  - `tag(text, ...)` name bar on the panel bottom; `bar(text, ...)` dark-red hook bar (full face or `split=True`).
- `tweet_war(out, dur, cards)` - circle-PiP: host circle on top, tweets rising in one by one as each author is named, yellow marker on a spoken phrase. Wire it like the template (panel slides up, PiP slides in 0.5 s later, V12 face scaled into the circle with `pip_face_motion(face_center=...)`, V13 overlay).
- `share_button()` on V14 at the very end.

## 4. Review checklist (mistakes the user has caught before)

- [ ] Opening retake of **every** raw removed (re-transcribe the first 10 s of each; listen across every join in the preview - transcribe ~5 s around each join with `clip_timestamps`).
- [ ] Last word of each raw not clipped (cut after silencedetect's silence start, not Whisper's word end).
- [ ] Circle-PiP enters ~0.5 s after the panel leaves; no overlap.
- [ ] Every clip's used range is clean (no outros, other channels' logos, burned captions).
- [ ] Card edges: no black line at the left (crop box x<0), logo complete (not "DECCAN HERAL"), body text readable, no sliced lines.
- [ ] Irrelevant clip called out by the user -> drop it to full face, don't swap in another.
- [ ] Flagged lines carry no text graphic.
- [ ] Length < 2:59; `mpdecimate` 150/150 on 5 s stretches; one face offset per take in the `.fcpxml`.
- [ ] Contact sheet of one frame per beat (half-res preview) looked at before the final render.
- [ ] Deliver `05_exports/shorts/<ID>_final.mp4` (1080x1920, 30 fps), verified with ffprobe.
