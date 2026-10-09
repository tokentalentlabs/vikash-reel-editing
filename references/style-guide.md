# Reel Style Guide (from 5 reference Shorts)

Format: 1080×1920, 30 fps, 90–180 s. One creator talking to a handheld/selfie camera, news-commentary tone.

## Layout

| Mode | When | Layout |
|---|---|---|
| **Full face** | Hook (first 0–1 s), opinion stretches, ending | Talking head fills frame |
| **Split screen** (main mode) | Whenever a fact, person, article or clip is mentioned | Top ~33% (≈ 0–630 px) = visual · **orange divider line** (~8 px, `#F39A1E`) · bottom ~67% = talking head, shifted down ~470 px so the face sits below the divider |
| **Floating card** | Quick references while staying on face | White-bordered photo or article card over the face, lower third or centered |

- Top-panel visuals change every **2–4 s** while facts are being listed, then the video returns to full face for long opinion stretches.
- Transitions between top visuals: **push left with motion blur, 8–10 frames** (no hard cuts). Full ANIMATION rules: `ANIMATION.md`.
- New panel types from the editors: photo with a blur-fill background and slow Ken Burns, stacked red pills sliding in per spoken item, icon-circle flow diagrams with drawn arrows, up to 3 stacked clips in the circle-PiP, and simple infographics (1–2 per video max).
- No burned-in word-by-word captions.

## Graphic elements

1. **Hook text bar**: dark red box `#7A1414`, thin white stroke, white **bold uppercase** sans (Montserrat ExtraBold/Black), centered in the lower-middle of the full-face shot. Examples: "SC/ST ACT MISUSE" → "WATCH TILL THE END". Swaps every ~1–2 s.
   - **Placement: on the neck / collar, never over the mouth or face.** Full face: y ≈ 1250 (`BAR_Y_FULL`). Split screen (face shifted down 470 px): y ≈ 1610 (`BAR_Y_SPLIT`). Check the frame. If the host leans in and the chin drops lower, move the bar down.
2. **Name tag**: same dark red rounded bar with white bold caps, sitting at the bottom of the top panel over photos (e.g. "DEEPANSHU SHOKEEN").
3. **Person ID card**: white background, rounded-corner photo, orange pill `#F07A1F` with the white bold name plus a smaller title line underneath ("Chief Minister of Bihar").
4. **Caption label**: white rounded box, black bold text (e.g. "Rohith Vemula 2.0"), over a single photo or a side-by-side photo pair.
5. **Article highlight** (the core technique): clean article screenshot (masthead + headline + first paragraph) on white.
   - *Black highlight*: headline/sentence gets a black bar and the text turns white. The bar **wipes left→right** in sync with the voiceover.
   - *Yellow marker*: yellow `#FFD84D` bar wipes behind the headline text (normal black text stays).
6. **Callouts on footage/screens**: red arrow + red hand-drawn circle (on CCTV and video stills), blue hand-drawn circle or bracket on documents.
7. **Data/list cards**: custom white cards, e.g. an election-results table with the key row in black, or "2 MAJOR QUESTIONS" with a yellow-highlighted heading, small orange "QUESTION 01" labels and bold question text.

## Source whitelist (strict — no other news outlets)
- **National:** ANI, PIB, Hindustan Times, NDTV, The Print, India Today, The Hindu, Indian Express, Economic Times, Deccan Herald, LiveMint
- **International:** Reuters, AP News, BBC, CNN, Guardian, DW, NPR, SCMP, WION, CNBC

## Article & document panels (must fill the panel)
- Clean card: outlet logo centred on top (`07_scripts_research/logos/`), headline, then story text running off the bottom edge. No nav bars, date rows, share buttons or "add as preferred source" pills.
- No white gaps anywhere; background matches the page (grey/dark pages get a same-colour matte).
- Highlights: black bar or yellow marker on light pages, yellow marker with black text on dark pages.
- Only show the page that proves the line being said (e.g. SC/ST cell *about* page, not its contact page).
- Other reference elements: X/Twitter post screenshots with a yellow-highlighted phrase, red location pill (e.g. "Bihar"), custom charts/infographics, "SHARE" button at the end.

- Cards must feel complete: logo → headline → subheading (small grey context line) → one or two full body paragraphs, key sentence highlighted as it's spoken. Never cut a line at the panel edge.

## Circle-PiP layout (for video clips)
- Dark background with a faint grid; host in a large white-bordered circle at the top centre.
- **Host framing in the circle = bust shot**: face + neck + a bit of shoulder, face ≈ 45–55 % of the circle's height, eyes slightly above centre. Never a face-filling close-up. `pip_face_motion()` defaults to 50 % scale with the face lifted above centre (≈ 0.48 is the lowest scale that still covers the circle without black edges).
- One or two clips stacked below in rounded frames with thin white borders.
- Each clip gets a dark-red caption bar on its bottom edge: date + event with the key word in bold — a place, name or any key phrase (e.g. "26 September Protest in **LPU**").
- Use for multiple clips / a sequence of events; keep the split screen for single clips and articles.

## Edit rules
- **Multiple raws per video:** join 2–3 files in upload order with tight joins; edit as one timeline.
- **No cuts** in the talking-head take: one continuous shot, no punch-in zooms. Exceptions: drop opening retakes (keep the last clean start of each raw), and cut dead pauses at the very end of the last raw. See CLAUDE.md.
- **Edit type** is given per video: research-heavy (articles, tweets, documents) or video-heavy (real incident footage verified against the script, images second, minimal articles).
- **No blood or violence** in clips unless requested up front, and blurred even then.
- Creative direction (beat sheet + mockup frame) is approved before building.
