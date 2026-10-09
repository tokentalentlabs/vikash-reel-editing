# Animation & Motion Rules (learned from 5 pro-editor reels)

Source reels: `~/Documents/Vikash animation/Edited video/`: 153 (IIT Bombay), Video 154 (Smit Machchhar, the editor's version of our SMIT build), Ethanol Scam, UPI/MDR, "vikash pause, clip play with full sound". All 1080×1920 at 29.97 fps, 2:30–3:00 long.
Timings below were measured frame by frame (1 frame ≈ 33 ms).

## 1. Core principle: nothing pops in or out
Every element that enters or leaves the frame moves. The editors never do hard on/off. Most moves are fast: **6–10 frames (0.2–0.35 s), ease-out (fast start, soft landing), with directional motion blur** while moving. Our v1 SMIT build cut everything hard, which is a big part of why it felt choppy.

| Element | Entrance | Exit | Duration |
|---|---|---|---|
| Top panel → next top panel | **Push left**: new panel slides in from the right while the old one slides out left, motion-blurred | (same move) | 8–10 f |
| Full face → split (panel appears) | Panel area slides down from the top / face slides down to the split position together | — | 8–10 f |
| Split → full face (panel leaves) | — | **Panel slides up out of frame and the face glides up to full-frame** in the same move (never a jump cut of the face) | 12–15 f |
| Article / tweet card (on matte) | Slides in from the left or rises from the bottom with motion blur | Slides off left | 8–12 f |
| Tweet card inside circle-PiP | **Rises from the bottom + scales 60→100 %**, heavy motion blur, ease-out | — | ~18 f |
| PiP clips (stacked) | Rise from the bottom one after another, **staggered ~3 f**, motion blur | — | ~12 f each |
| Circle-PiP scene (incl. host circle) | **Panel slides up first; ~0.5 s later the whole PiP scene, circle included, slides in from the left** (12 f). Exit: slides out right while the next panel comes down. Never overlap the panel exit with the PiP entrance (user feedback, UJJ v3). | slide out right | 12 f in / 9 f out |
| Hook / text bar (dark red) | **Fade + rise ~20 px**, then keeps drifting up slowly (≈ 20 px over 0.4 s) | Fade | 3–4 f in |
| Name bar on a photo | Comes in ~0.5–1 s after the photo, slide up from the panel bottom edge | With the panel | 6 f |
| Pills / list rows (red rounded boxes) | **Slide in from the right** with motion blur, one per spoken item, stacking downward | With the panel | 8–10 f each |
| Diagram nodes (icon circles) | **Scale-pop 0→105→100 %** (slight overshoot) | — | 6–8 f |
| Diagram arrows | **Draw on** along the path (stroke reveal), then the next node pops at the arrow head | — | 10–15 f |
| Highlight (yellow marker / black bar) | Wipes left→right in sync with the words (same as now; 1.5–3 s per line) | stays until the panel leaves | per words |
| SHARE button (end) | Layered wipe: **black bar wipes in → white wipes over it → blue SHARE wipes in** left→right | — | ~25 f total |
| Still photo panels | **Slow Ken Burns zoom-in ~5 % over the shot** (never fully static) | — | whole shot |

## 2. Layout-transition rules
- The face is always the same continuous take. Layout changes move the face (animated Transform) and never cut it.
- Split/full switches happen on a **phrase boundary**, not mid-word.
- Panel swaps every 2–4 s while facts are listed. During long opinion stretches the panel leaves (slides up) and the face goes full.
- The orange divider always travels with the panel edge during those moves.

## 3. Panel content patterns seen
- **Photo + blur-fill:** a portrait or narrow photo is centred and the panel's leftover width is filled with an enlarged, blurred copy of the same photo. No black or white bars.
- **Video clip in the top panel instead of an article** whenever real footage of the claim exists (e.g. a Modi speech clip with burned subtitles instead of the DH article). Prefer footage over article cards in video-heavy edits.
- **Circle-PiP with up to 3 stacked clips** (e.g. Modi / Netanyahu / Trump speaking) for "X ne ki, Y ne ki, Z ne ki" lists. Each clip enters staggered as its name is said.
- **Two tweets stacked in the PiP** (second one rises in under the first when it's mentioned).
- **Graphic or violent footage is heavily blurred** (strong Gaussian, faces and blood unreadable), shown only briefly. See CLAUDE.md: avoid it unless requested.
- **Article pages:** clean white page, yellow marker on the spoken sentence; the panel scrolls or pushes to the next paragraph rather than cutting.

## 4. Host freeze + clip with full sound (only when the user asks)
When requested ("pause host, play clip with sound"):
- The host's face **freezes on a neutral, mouth-closed frame** (FCP: Hold Frame) while the clip plays in the top panel **with its own audio at full level**.
- The host's voice track has a gap for exactly that duration. The timeline gets longer; the host take itself isn't cut, it resumes from the next frame.
- The clip can push to a second clip with the same push-left move.
- Default (not requested): clips play **muted** under the host's continuous voice.

## 5. Infographics (max 1–2 per video, only when they explain something words can't)
Style from the references (P2P/P2M cards, ₹1,000/₹2,000/₹3,000 MDR card, donut + bar chart, flow diagram):
- White rounded card with a soft drop shadow on a white or very light panel, flat icons in a **blue gradient** (`#5B9BE8 → #3A78D6`) or **dark-red circles** (`#7A1414`) with white icons.
- Heavy black sans titles (P2P), big bold numbers, small spaced-caps labels (PAYMENT / RECEIVES).
- One key number in a solid blue box; a "THE MAIN POINT" footer strip with a target icon summarising it.
- Charts: donut for share-of-count, bars for share-of-value, black for the highlighted slice, light blue for the rest, % labels on top.
- **Build up as spoken:** nodes pop, arrows draw, numbers appear one by one. Never show the finished infographic all at once.

## 6. Implementation (reel_kit, built for UJJ_Ujjain_v3 — use `assets/templates/build_research_heavy.py` (or `build_video_heavy.py`) as the template)
- Panel items use track `P` (base) / `H0..H2` (highlights or pills) plus a group id; dividers use `D`. After adding everything, call `animate_layout(items, split_windows)`: it adds the slide-down entrance, push-left swaps, slide-up exit and the face glide, and spreads the groups over V2–V9 (divider V10). Text goes on V11, the SHARE clip on V12.
- Presets: `bar_motion`, `tag_motion`, `pill_motion` (Item `motion=`), `pill_layers`, `photo_panel` (blur-fill + Ken Burns), `share_button`, and `pip_layout` (clips rise in staggered). Merge split windows that touch across a take join into one window.
- Not done yet: motion blur (FCP has no per-clip motion blur; the moves are short enough to read cleanly without it).

### Older notes
- Moves are written as keyframed `adjust-transform` position/scale (and opacity via `adjust-blend amount`) on the connected clip in the `.fcpxml`, so they stay editable in Final Cut. Motion blur: tell the user to enable FCP's motion blur on those clips, or bake it into a rendered ProRes 4444 alpha clip for complex builds (diagrams, PiP stacks, SHARE).
- Ease-out curve: FCP keyframe `interp="easeOut"`. Overshoot pops are baked into rendered clips.
- The half-res preview must render the same moves (otherwise preview and FCP disagree).
- Keep every animated element frame-aligned (`src_frame` rules in CLAUDE.md) so motion never stutters.
