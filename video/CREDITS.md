# Credits and licences — DNT-Scout film

Everything in this film is our own work, public-domain data, or the output of permissively licensed
tools. **No stock footage, no third-party music, no AI-generated imagery, no voice cloning.**

## What is on screen

| Material | Source | Licence / status |
|---|---|---|
| Enrichment curve, permutation null distribution, class counts, every figure | computed in this repository (`results/`) and drawn by `video/tools/vis.py` | ours (MIT) |
| Permutation null (999 values) | independent audit, 2026-10-23; copied into `results/audit/permutation_null.csv` and re-summarised by us | ours to republish; the audit was commissioned for this project |
| Effect concentrations, class counts | US EPA network-formation assay, Shafer et al. 2019, DOI 10.23719/1503191 | US Government work, public domain |
| SciencePal screen captures | the **public** share link of our own agent run, captured headless at 1920×1080 by `video/tools/capture_sciencepal.py` | ours; captured from a page anyone can open |
| Title cards, lower thirds, tag chips, animation | `video/tools/vis.py` (Pillow + matplotlib) | ours |
| Background score | synthesised in code — `music_bed()` in `video/tools/build_video.py`: three sine chords, low-passed, 26 dB under the narration | ours |
| Narration | synthetic voice `bm_george` of Kokoro-82M v1.0 (hexgrad) | Apache-2.0, model and voices |
| Subtitles (EN) | written by us; generated from the narration timings, in the written form | ours |
| Font | DejaVu Sans | Bitstream Vera / DejaVu licence (free use) |

## The voice

`kokoro:bm_george@1.0` — a **stock voice of an open model**, not a clone or imitation of any real
person, and not an extract of any other recording. It is the same voice used in an earlier film by
this author, which is a continuity-of-style choice; the voice is regenerated here from the model
itself, so nothing from that earlier production is carried over. Synthesised offline on CPU,
sentence by sentence, with silence trimmed at each end and a fixed 0.28 s pause between sentences.

## Models and software

| Component | Version | Licence | Use |
|---|---|---|---|
| Kokoro-82M v1.0 | hexgrad/Kokoro-82M | Apache-2.0 | narration |
| misaki + spaCy `en_core_web_sm` | 3.8.0 | MIT | English grapheme-to-phoneme for the TTS |
| torch (CPU build) | 2.14.1+cpu | BSD-3-Clause | runs the TTS model |
| Pillow | 13.x | MIT-CMU | frame composition |
| matplotlib | 3.11.x | matplotlib licence | the data plots inside the frames |
| NumPy | 2.x | BSD-3-Clause | numerics, the score |
| Playwright + Chromium headless | 1.x | Apache-2.0 | SciencePal captures |
| FFmpeg | 7.1.5 | GPL build, used as a tool | encoding, subtitle burn-in, loudness normalisation |

No GPU was used: the two RTX 3090s on the build machine stayed free. Kokoro runs on CPU, and the
animation is drawn, not generated.

## Two rules the film follows

1. **Every scene says what kind of thing it is showing.** A chip in the top-right corner reads
   MEASURED, RESULTS, ILLUSTRATION or LIVE APP. A viewer never has to guess whether a curve is data
   or decoration.
2. **No number is typed into a frame by hand.** Everything on screen is read from a results file by
   `vis.N()` and logged, with its source path, to `video/numbers_onscreen.json`. Figures quoted from
   the independent audit rather than recomputed by us are flagged `quoted_not_recomputed` in that
   same log.

## Reproducing it

```bash
uv venv --python 3.12 video/.venv-tts
uv pip install --python video/.venv-tts/bin/python torch --index-url https://download.pytorch.org/whl/cpu
uv pip install --python video/.venv-tts/bin/python kokoro soundfile num2words playwright
video/.venv-tts/bin/python -m playwright install --with-deps chromium

video/.venv-tts/bin/python video/tools/tts.py --all          # narration + timings
python video/tools/capture_sciencepal.py                     # live-app frames
python video/tools/build_video.py --all                      # frames, subtitles, encode
```
