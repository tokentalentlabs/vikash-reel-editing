"""Word timings for Hindi raws via short Whisper windows (long VAD segments drop words).
usage: transcribe_windows.py OUT_DIR RAW [RAW ...]   -> OUT_DIR/<stem>_words.json"""
import json
import subprocess
import sys
from pathlib import Path

from faster_whisper import WhisperModel

out_dir = Path(sys.argv[1])
out_dir.mkdir(parents=True, exist_ok=True)
m = WhisperModel("large-v3", device="cpu", compute_type="int8")
for raw in sys.argv[2:]:
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", raw],
                               capture_output=True, text=True).stdout)
    words, t = [], 0.0
    while t < dur:
        e = min(dur, t + 8.0)
        segs, _ = m.transcribe(raw, language="hi", word_timestamps=True, beam_size=5,
                               condition_on_previous_text=False, clip_timestamps=[t, e])
        ws = [{"start": round(w.start, 2), "end": round(w.end, 2), "word": w.word} for s in segs for w in (s.words or [])]
        ws = [w for w in ws if t <= w["start"] < e]
        words += ws
        print(Path(raw).stem, f"{t:5.1f}", "".join(w["word"] for w in ws), flush=True)
        t = e
    (out_dir / f"{Path(raw).stem}_words.json").write_text(json.dumps(words, ensure_ascii=False, indent=0))
