"""Narration for the DNT-Scout film. One voice variable controls everything.

Voice spec: ``<engine>:<voice>[@<speed>]`` — read from ``video/VOICE_CHOICE.txt`` unless overridden.
The film uses ``kokoro:bm_george@1.0``: Kokoro-82M v1.0 (hexgrad), Apache-2.0, British English,
synthesised offline on CPU. It is a stock voice of an open model, **not a clone of anyone**.

Synthesis is sentence by sentence, each sentence trimmed of its leading and trailing silence and
followed by a fixed pause, which is what gives the narration a steady documentary cadence instead
of the rushed one a single long call produces. The same split gives each sentence a start and end
time, and those times drive both the subtitles and the animation timing — so a scene can never
drift out of sync with what is being said about it.

    python tools/tts.py --scene S1 --out audio/S1.wav
    python tools/tts.py --all
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

VIDEO = Path(__file__).resolve().parents[1]
SR = 24000
PAUSE_SENTENCE, PAUSE_CLAUSE, PAUSE_PARA = 0.28, 0.12, 0.52
DEFAULT_VOICE = "kokoro:bm_george@1.0"

#: display text -> spoken text. Subtitles keep the display form; only the synthesiser sees these.
SPOKEN = [
    (r"(\d+)\s*/\s*(\d+)", r"\1 of \2"),
    (r"µM", "micromolar"),
    (r"(\d)%", r"\1 per cent"),
    (r"\bUS EPA\b", "U.S. E.P.A."),
    (r"\bEPA\b", "E.P.A."),
    (r"\bMEA\b", "M.E.A."),
    (r"\bDNT-Scout\b", "D.N.T. Scout"),
    (r"\bSciencePal\b", "Science-Pal"),
    (r"\bROC AUC\b", "area under the curve"),
    (r"\bp = 0\.001\b", "p equals zero point zero zero one"),
]


def spoken(text: str) -> str:
    for a, b in SPOKEN:
        text = re.sub(a, b, text)
    return text


def voice_spec(cli: str | None = None) -> str:
    if cli:
        return cli
    f = VIDEO / "VOICE_CHOICE.txt"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                return line
    return DEFAULT_VOICE


def sentences(display: str) -> list[str]:
    """Split on sentence and clause boundaries, keeping the punctuation with the sentence."""
    return [s for s in (x.strip() for x in re.split(r"(?<=[.?!:;])\s+", display.strip())) if s]


def _trim(a: np.ndarray) -> np.ndarray:
    """Cut the silence Kokoro leaves at each end, keeping 40 ms of margin."""
    if a.size == 0:
        return a
    env = np.convolve(np.abs(a), np.ones(240) / 240, mode="same")
    on = np.where(env > 0.01 * env.max())[0] if env.max() > 0 else np.array([], dtype=int)
    return a[max(0, on[0] - 960): on[-1] + 960] if on.size else a


_PIPE: dict = {}


def _kokoro(text: str, voice: str, speed: float) -> np.ndarray:
    from kokoro import KPipeline
    if "b" not in _PIPE:
        _PIPE["b"] = KPipeline(lang_code="b", repo_id="hexgrad/Kokoro-82M")   # British English
    parts = [a.numpy() if hasattr(a, "numpy") else np.asarray(a)
             for _g, _p, a in _PIPE["b"](text, voice=voice, speed=speed, split_pattern=r"\n+")]
    return np.concatenate(parts).astype(np.float32) if parts else np.zeros(0, np.float32)


def narrate(paragraphs: list[str], spec: str | None = None):
    """Synthesise a scene. Returns (audio, cues) where each cue times one displayed sentence."""
    engine, rest = voice_spec(spec).split(":", 1)
    voice, _, sp = rest.partition("@")
    speed = float(sp) if sp else 1.0
    assert engine == "kokoro", "only the kokoro engine is wired up; see VOICE_CHOICE.txt"

    out, cues, t = [], [], 0.0
    for pi, para in enumerate(paragraphs):
        for si, disp in enumerate(sentences(para)):
            a = _trim(_kokoro(spoken(disp), voice, speed))
            dur = len(a) / SR
            cues.append({"text": disp, "start": round(t, 3), "end": round(t + dur, 3)})
            out.append(a)
            gap = PAUSE_CLAUSE if disp.rstrip().endswith((":", ";")) else PAUSE_SENTENCE
            t += dur + gap
            out.append(np.zeros(int(SR * gap), np.float32))
        if pi < len(paragraphs) - 1:
            extra = PAUSE_PARA - PAUSE_SENTENCE
            out.append(np.zeros(int(SR * extra), np.float32))
            t += extra
    audio = np.concatenate(out) if out else np.zeros(0, np.float32)
    return audio, cues


def scene_text(scene_id: str) -> list[str]:
    """Pull one scene's narration out of script.md: the block-quoted lines under its heading."""
    md = (VIDEO / "script.md").read_text(encoding="utf-8")
    m = re.search(r"^##\s+%s\b.*?$(.*?)(?=^##\s|\Z)" % re.escape(scene_id), md,
                  re.S | re.M)
    assert m, "scene %s not found in script.md" % scene_id
    paras, cur = [], []
    for line in m.group(1).splitlines():
        s = line.strip()
        if s.startswith(">"):
            body = s.lstrip(">").strip()
            if body:
                cur.append(body)
            elif cur:
                paras.append(" ".join(cur)); cur = []
        elif cur:
            paras.append(" ".join(cur)); cur = []
    if cur:
        paras.append(" ".join(cur))
    return paras


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--voice")
    a = ap.parse_args()
    import soundfile as sf
    ids = [s for s in re.findall(r"^##\s+(S\d+)\b", (VIDEO / "script.md").read_text(encoding="utf-8"),
                                 re.M)] if a.all else [a.scene]
    (VIDEO / "audio").mkdir(exist_ok=True)
    manifest = {}
    for sid in ids:
        paras = scene_text(sid)
        audio, cues = narrate(paras, a.voice)
        wav = VIDEO / "audio" / f"{sid}.wav"
        sf.write(wav, audio, SR)
        manifest[sid] = {"wav": wav.name, "duration": round(len(audio) / SR, 3),
                         "words": sum(len(p.split()) for p in paras), "cues": cues}
        wpm = manifest[sid]["words"] / max(manifest[sid]["duration"], 1e-6) * 60
        print("%s  %5.1f s  %3d words  %5.1f wpm  %d sentences"
              % (sid, manifest[sid]["duration"], manifest[sid]["words"], wpm, len(cues)))
    (VIDEO / "narration.json").write_text(json.dumps(
        {"voice": voice_spec(a.voice), "sample_rate": SR, "scenes": manifest}, indent=1),
        encoding="utf-8")
    total = sum(v["duration"] for v in manifest.values())
    print("total narration %.1f s (%d:%02d)" % (total, int(total // 60), int(total % 60)))


if __name__ == "__main__":
    sys.exit(main())
