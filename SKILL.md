---
name: lyric-video
description: >
  Turn a song, a cover image and (optionally) plain lyrics text into a finished lyric
  video — no SRT needed, timings are generated automatically with offline speech
  recognition and fuzzy alignment that tolerates typos in the lyrics. Two looks:
  Spotify "now playing" and cinematic motivational (Kalam Hindi font, word highlight).
  Use when the user asks for a lyric video, karaoke video, Spotify-style lyrics edit,
  or a motivational lyrics reel.
---

# Lyric Video skill

**Input the user gives you:** an audio file, a cover image, and the lyrics as plain text
(optional). **You deliver:** one finished `.mp4`. The user never has to supply an SRT —
`auto_srt.py` builds it from the audio.

## Do this

```bash
pip install pillow imageio-ffmpeg vosk          # ffmpeg ships with imageio-ffmpeg

python scripts/make_video.py \
    --audio song.mp3 --cover cover.png --lyrics lyrics.txt \
    --title "Song Name" --artist "Artist Name" \
    --style spotify --out lyric_video.mp4
```

That single command: recognises speech → aligns the user's lyrics to it → writes the SRT →
renders the video in chunks → concatenates → writes `lyric_video.mp4`.

- `--style spotify` (default) — blurred cover background, album card, progress bar,
  smoothly scrolling lyrics.
- `--style cinematic` — full-bleed background (pass `--bg plate.png`, or one is generated),
  2.35:1 letterbox, Kalam font, word-by-word highlight.
- `--start 9.6 --duration 20` — teaser clip.
- No cover? One is generated from the title. No lyrics? ASR text is used.

## Inputs, and what to do when they are missing

| Input | Notes | If missing |
|---|---|---|
| Audio | mp3 / m4a / wav | required — ask for it |
| Cover | square ≥1000×1000 | generated procedurally; or make one in Figma (`generate_image`, prompt in PROMPTS.md) |
| Lyrics text | plain text, one line per lyric line | ASR text is used, timings still automatic |
| Title / artist | text | inferred from the cover or left generic |
| Language | `--lang hi` (default) or `en` | pick from the lyrics script |

Typos are expected and handled: both sides are normalised (punctuation, nukta, case) and
words are matched with a fuzzy ratio, so "कोलम्बस" vs "कोलंबस" or "आईंस्टीन" vs "आइंस्टाइन"
still line up. Words that cannot be matched get interpolated between their neighbours.

## Pipeline (what the scripts do)

1. `auto_srt.py` — decodes audio to 16 kHz PCM, runs Vosk (offline, downloads a ~40–80 MB
   model once), optionally constrains decoding with the user's lyric lines as a grammar,
   aligns them with `difflib` + fuzzy matching, and writes one SRT cue per lyric line.
2. `spotify_lyrics.py` / `motivational_render.py` — render frames with Pillow, pipe raw
   frames into ffmpeg.
3. `make_video.py` — chunks the render (45 s per chunk by default, keeps memory < 2 GB),
   concatenates with `ffmpeg -f concat -c copy`.

## Quality bar

- Continuous motion, never stepped: interpolate the camera/scroll per frame.
- Active line bigger and brighter; neighbours shrink and dim in tiers.
- Auto-shrink long lines to a safe width; never clip text at the frame edge.
- Correct font per script: Devanagari lines need a Devanagari font (bundled in
  `assets/fonts/`), Latin lines need a Latin font. Never mix them in one string.
- One idea per frame: either the background moves or the text moves, not both hard.

## Verify before delivering

```bash
ffmpeg -ss 12 -i out.mp4 -frames:v 1 check.jpg   # 2–3 spots
```
Check: no clipped lines, one active line, no tofu/boxes (font problem), progress time
correct, audio in sync, bars/grade consistent.

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| Boxes instead of text | wrong font for the script | use `font_for(text, …)`; Devanagari fonts are in `assets/fonts/` |
| `mkl_malloc: failed to allocate memory` | 2 GB RAM + big model/audio | Vosk (used here) avoids this; if using whisper, chunk to 8–10 s |
| ffmpeg `Cannot allocate memory` | too many frames in flight | `--chunk 40`, `-threads 2`, `rc-lookahead=4` |
| Lyrics drift over time | alignment failed on a long instrumental gap | pass `--lyrics`; keep one lyric line per line of text |
| Background jumps | pre-rendered keyframes swapped, not blended | the bundled renderers blend/interpolate |
