import json
import sys
from pathlib import Path

from faster_whisper import WhisperModel

src = Path(sys.argv[1])
out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("07_scripts_research/scripts")
model_name = sys.argv[3] if len(sys.argv) > 3 else "large-v3"
out_dir.mkdir(parents=True, exist_ok=True)

model = WhisperModel(model_name, device="cpu", compute_type="int8")
# Short VAD chunks + no text conditioning: long Hindi segments otherwise drop whole stretches of speech.
segments, info = model.transcribe(
    str(src), language="hi", word_timestamps=True, beam_size=5,
    condition_on_previous_text=False,
    vad_filter=True, vad_parameters={"max_speech_duration_s": 12, "min_silence_duration_ms": 300},
)

data, lines = [], []
for s in segments:
    words = [{"start": round(w.start, 2), "end": round(w.end, 2), "word": w.word} for w in (s.words or [])]
    data.append({"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip(), "words": words})
    lines.append(f"[{s.start:6.2f} - {s.end:6.2f}] {s.text.strip()}")
    print(lines[-1], flush=True)

stem = src.stem
(out_dir / f"{stem}_transcript.json").write_text(json.dumps(data, ensure_ascii=False, indent=1))
(out_dir / f"{stem}_transcript.txt").write_text("\n".join(lines))
