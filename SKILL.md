---
name: lyric-video
description: >
  Generate a lyric video from an audio file and timed lyrics (.srt). Two built-in
  looks: a Spotify "now playing" style (blurred cover background, album card,
  progress bar, smoothly scrolling lyrics) and a cinematic motivational style
  (full-bleed background, Kalam Hindi font, word-by-word highlight, letterbox bars,
  slow continuous camera). Use when the user asks for a lyric video, karaoke video,
  Spotify-style lyrics edit, or a motivational lyrics reel.
---

# Lyric Video skill

Produce a finished `.mp4` lyric video from three inputs: **audio**, **cover art**, and
**timed lyrics**. Everything runs locally with Pillow + ffmpeg — no external API needed.

## Inputs you need

| Input | Format | Fallback if missing |
|---|---|---|
| Song | `.mp3` / `.m4a` / `.wav` | required |
| Cover art | square image ≥ 1000×1000 | `scripts/cover_art.py`, or Figma `generate_image` |
| Lyrics + timing | `.srt` (one cue per line) | transcribe + align (see below) |
| Title / artist | text | take from metadata or cover |
| Length | full song, or `--start` / `--duration` | full song |

Ask for anything missing **before** rendering — the song and the lyric timings decide
the whole build.

## Choose the style

**A. Spotify "now playing"** — `scripts/spotify_lyrics.py`
Use when the user says Spotify, now-playing, album card, or wants a clean, neutral edit.

**B. Cinematic motivational** — `scripts/motivational_render.py`
Use when the user shows a dramatic poster-style reference, wants Hindi lyrics in a
handwriting font (Kalam), or asks for reels/rap edits.

## Workflow

1. **Check inputs.** Audio duration, cover size, SRT cue count. If there is no SRT, build one:
   - Take the *official* lyrics text (user's or verified source). Never ship ASR text for a song.
   - Get word timings with `faster-whisper` (`word_timestamps=True`).
   - Align official words to ASR words with `difflib.SequenceMatcher`; interpolate unmatched
     words between their matched neighbours.
   - Emit an SRT where each line starts at its first word and ends at its last.
2. **Render in chunks** (45 s max per chunk on a 2 GB machine) and concatenate:
   ```bash
   printf "file 'p1.mp4'\nfile 'p2.mp4'\n" > parts.txt
   ffmpeg -f concat -safe 0 -i parts.txt -c copy full.mp4
   ```
3. **Verify** — extract 2–3 frames (`ffmpeg -ss <t> -frames:v 1`) and look at them:
   no clipped lines, one active line only, bars/grade consistent, progress time correct.
4. **Deliver** the mp4 (plus a 20 s teaser if the user wants one).

## Design rules that make it look "produced"

- Continuous motion, never stepped: interpolate the camera (or scroll) per frame.
- Active line is bigger and brighter; neighbours shrink and dim in tiers.
- Auto-shrink long lines to a safe width — never clip text at the edges.
- One idea per frame: background moves, text holds still (or vice versa).
- Keep a consistent palette; use one accent colour for progress and highlight.

## Pitfalls

- `mkl_malloc: failed to allocate memory` → audio chunks of 8–10 s for ASR; small models.
- ffmpeg `Cannot allocate memory` → shorter chunks, `-threads 2`, `rc-lookahead=4`.
- Background that jumps every second → pre-rendered keyframes are being swapped, not blended.
- Lyrics clipping → missing auto-shrink; check the `fit()` helper.
- Missing fonts → ship the TTF or fall back to DejaVu.

## Reference

- `briefs/Lyric_Video_Brief.md` — full spec, tokens, and self-contained renderer code.
- `README.md` — setup, commands, QA checklist, troubleshooting table.
