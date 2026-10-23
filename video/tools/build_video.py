"""Assemble the DNT-Scout film: frames, narration, subtitles, a synthesised score, one MP4.

Scene length is taken from the narration, never guessed: `tts.py` writes how long each scene's
voice track actually is, and the renderer draws exactly that many frames plus a short tail. A scene
therefore cannot run short of its own sentence or linger after it.

    python tools/build_video.py --frames        # render PNG frames
    python tools/build_video.py --assemble      # mux audio, burn subtitles, encode
    python tools/build_video.py --all
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

VIDEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(VIDEO / "tools"))

import vis  # noqa: E402

FPS = vis.FPS
TAIL = 0.55            # seconds of held frame after the last word of a scene
SR_A = 48000
FFMPEG = "ffmpeg"


# ------------------------------------------------------------------------------------- subtitles
def srt_time(t: float) -> str:
    h, rem = divmod(max(t, 0.0), 3600)
    m, s = divmod(rem, 60)
    return "%02d:%02d:%06.3f" % (h, m, s).__str__().replace(".", ",") if False else \
        "%02d:%02d:%02d,%03d" % (h, m, int(s), round((s - int(s)) * 1000))


def write_srt(narration: dict, path: Path):
    """One cue per spoken sentence, in the written form — not the pronunciation form."""
    lines, idx, offset = [], 1, 0.0
    for sid, _fn, _d in vis.SCENES:
        sc = narration["scenes"][sid]
        for cue in sc["cues"]:
            text = cue["text"]
            if len(text) > 92:                      # wrap long sentences onto two lines
                cut = text.rfind(" ", 0, 92)
                text = text[:cut] + "\n" + text[cut + 1:]
            lines.append("%d\n%s --> %s\n%s\n" % (idx, srt_time(offset + cue["start"]),
                                                  srt_time(offset + cue["end"]), text))
            idx += 1
        offset += sc["duration"] + TAIL
    path.write_text("\n".join(lines), encoding="utf-8")
    return offset


# ------------------------------------------------------------------------------------- the score
def music_bed(seconds: float, seed: int = 20261023) -> np.ndarray:
    """A quiet synthesised pad. Written here in code so the film owes nothing to a music licence.

    Three slow sine chords in A minor, low-passed and deeply attenuated, with a long fade at each
    end. It sits about 26 dB under the narration: present enough to remove the silence between
    sentences, never enough to compete with a word.
    """
    rng = np.random.default_rng(seed)
    n = int(seconds * SR_A)
    t = np.arange(n) / SR_A
    chords = [(110.0, 164.81, 220.0), (98.0, 146.83, 196.0), (82.41, 130.81, 164.81)]
    out = np.zeros(n, np.float32)
    seg = seconds / len(chords)
    for i, chord in enumerate(chords):
        env = np.clip(1.0 - np.abs((t - (i + 0.5) * seg) / (seg * 0.85)), 0, 1) ** 1.6
        for f in chord:
            drift = 1.0 + 0.0008 * np.sin(2 * np.pi * (0.03 + 0.01 * rng.random()) * t)
            out += (env * np.sin(2 * np.pi * f * drift * t)).astype(np.float32) / len(chord)
    # one-pole low pass, twice, to take the edge off
    a = math.exp(-2 * math.pi * 900 / SR_A)
    for _ in range(2):
        y = np.empty_like(out)
        acc = 0.0
        for i in range(0, n, 4096):                     # chunked, so it stays fast
            blk = out[i:i + 4096]
            for j, v in enumerate(blk):
                acc = a * acc + (1 - a) * v
                y[i + j] = acc
        out = y
    fade = int(SR_A * 2.0)
    out[:fade] *= np.linspace(0, 1, fade)
    out[-fade:] *= np.linspace(1, 0, fade)
    return (out / (np.abs(out).max() + 1e-9) * 0.05).astype(np.float32)


# ---------------------------------------------------------------------------------------- frames
def render_frames(narration: dict, only: str | None = None):
    out = VIDEO / "frames"
    out.mkdir(exist_ok=True)
    total = 0
    for sid, fn, _budget in vis.SCENES:
        if only and sid != only:
            continue
        dur = narration["scenes"][sid]["duration"] + TAIL
        n = int(round(dur * FPS))
        d = out / sid
        d.mkdir(exist_ok=True)
        for i in range(n):
            img = fn(i / FPS, dur)
            img.save(d / ("%05d.png" % i), compress_level=1)
            if i % 60 == 0:
                print("  %s %4d/%4d" % (sid, i, n), flush=True)
        print("%s rendered %d frames (%.1f s)" % (sid, n, dur), flush=True)
        total += n
    vis.dump_numbers(VIDEO / "numbers_onscreen.json")
    print("total %d frames, %.1f s" % (total, total / FPS))


# -------------------------------------------------------------------------------------- assemble
def assemble(narration: dict):
    import soundfile as sf
    work = VIDEO / ".build"
    work.mkdir(exist_ok=True)

    # one continuous narration track, scenes separated by their tail
    pieces = []
    for sid, _fn, _b in vis.SCENES:
        a, sr = sf.read(VIDEO / "audio" / f"{sid}.wav", dtype="float32")
        if sr != SR_A:
            import scipy.signal as ss
            a = ss.resample_poly(a, SR_A, sr).astype(np.float32)
        pieces += [a, np.zeros(int(SR_A * TAIL), np.float32)]
    voice = np.concatenate(pieces)
    dur = len(voice) / SR_A
    mix = voice + music_bed(dur)[:len(voice)]
    sf.write(work / "mix.wav", mix, SR_A)

    # one frame list, in order
    lst = work / "frames.txt"
    with lst.open("w", encoding="utf-8") as f:
        for sid, _fn, _b in vis.SCENES:
            for p in sorted((VIDEO / "frames" / sid).glob("*.png")):
                f.write("file '%s'\nduration %.6f\n" % (p.as_posix(), 1 / FPS))
        f.write("file '%s'\n" % p.as_posix())

    srt = VIDEO / "subs_en.srt"
    out = VIDEO / "dnt_scout_film.mp4"
    cmd = [FFMPEG, "-y", "-loglevel", "error", "-stats",
           "-f", "concat", "-safe", "0", "-i", str(lst),
           "-i", str(work / "mix.wav"),
           "-vf", ("subtitles=%s:force_style='FontName=DejaVu Sans,FontSize=19,"
                   "PrimaryColour=&H00F6F0EC,OutlineColour=&H90000000,BorderStyle=3,Outline=2,"
                   "Shadow=0,MarginV=42'" % srt.as_posix().replace(":", r"\:")),
           "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
           "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
           "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)]
    print("encoding %s (%.1f s)..." % (out.name, dur), flush=True)
    subprocess.run(cmd, check=True)
    print("wrote %s  %.1f MB" % (out, out.stat().st_size / 1e6))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", action="store_true")
    ap.add_argument("--assemble", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--scene")
    a = ap.parse_args()
    narration = json.loads((VIDEO / "narration.json").read_text(encoding="utf-8"))
    if a.frames or a.all or a.scene:
        render_frames(narration, a.scene)
    if a.assemble or a.all:
        total = write_srt(narration, VIDEO / "subs_en.srt")
        print("subtitles written, film runs %.1f s (%d:%02d)"
              % (total, int(total // 60), int(total % 60)))
        assemble(narration)


if __name__ == "__main__":
    sys.exit(main())
